"""Desktop adapter for the GPL-3.0 KomootGPX project."""
import json
import re
import threading
from pathlib import Path
from urllib.parse import urlparse
import xml.etree.ElementTree as ET
import requests
from vendor.komootgpx.api import KomootApi
from vendor.komootgpx.gpxcompiler import GpxCompiler

class Cancelled(Exception):
    pass

class DesktopApi(KomootApi):
    def __init__(self, stop):
        super().__init__()
        self.stop = stop

    def _KomootApi__send_request(self, url, auth, critical=True):
        parsed = urlparse(url)
        if parsed.scheme != 'https' or parsed.hostname != 'api.komoot.de':
            raise RuntimeError('Unerwartete API-Adresse.')
        for attempt in range(3):
            if self.stop.is_set():
                raise Cancelled()
            try:
                response = requests.get(url, auth=auth, timeout=(10, 30), allow_redirects=False)
            except requests.RequestException:
                if attempt == 2:
                    raise RuntimeError('Komoot nicht erreichbar. Verbindung prüfen.') from None
            else:
                if response.status_code == 200:
                    return response
                if response.status_code in (401, 403):
                    raise RuntimeError('Anmeldung oder Zugriff abgelehnt. Komoot-E-Mail und Passwort prüfen.')
                if response.status_code != 429 and response.status_code < 500:
                    raise RuntimeError(f'Komoot antwortet mit HTTP {response.status_code}.')
                if attempt == 2:
                    raise RuntimeError(f'Komoot vorübergehend nicht verfügbar (HTTP {response.status_code}).')
            if self.stop.wait(2 ** (attempt + 1)):
                raise Cancelled()

def valid_gpx(path):
    try:
        root = ET.parse(path).getroot()
        return root.tag.split('}')[-1] == 'gpx' and any(e.tag.split('}')[-1] == 'trkpt' for e in root.iter())
    except (OSError, ET.ParseError):
        return False

def render_gpx(tour, api):
    return GpxCompiler(tour, api, no_poi=True).generate()

def export_tours(api, folder, stop, emit, render=render_gpx):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    result = dict(saved=0, skipped=0, failed=0, cancelled=False)
    report = []
    if stop.is_set():
        result['cancelled'] = True
        return result
    emit('status', 'Abgeschlossene Touren werden ermittelt …')
    tours = [t for t in api.fetch_tours(tour_type='tour_recorded').values() if t.get('type') == 'tour_recorded']
    emit('total', len(tours))
    for index, tour in enumerate(tours, 1):
        if stop.is_set():
            result['cancelled'] = True
            break
        tid = str(tour['id'])
        if not re.fullmatch(r'\d+', tid):
            raise RuntimeError('Ungültige Tour-ID von Komoot.')
        path = folder / f'tour-{tid}.gpx'
        temp = path.with_suffix('.gpx.part')
        row = {'id': tid, 'name': tour.get('name', tid), 'file': path.name}
        try:
            if valid_gpx(path):
                result['skipped'] += 1
                row['status'] = 'bereits vorhanden'
            else:
                detail = api.fetch_tour(tid, language='de')
                if detail.get('type') != 'tour_recorded':
                    raise RuntimeError('Tour ist keine abgeschlossene Aktivität.')
                xml = render(detail, api)
                temp.write_text(xml, encoding='utf-8')
                if not valid_gpx(temp):
                    raise RuntimeError('GPX enthält keinen gültigen Track.')
                if stop.is_set():
                    raise Cancelled()
                temp.replace(path)
                result['saved'] += 1
                row['status'] = 'gespeichert'
        except Cancelled:
            result['cancelled'] = True
            break
        except Exception as exc:
            result['failed'] += 1
            row['status'] = 'fehlgeschlagen'
            row['error'] = str(exc)
        finally:
            temp.unlink(missing_ok=True)
        report.append(row)
        emit('progress', index, len(tours), row)
        if stop.wait(0.25):
            result['cancelled'] = index < len(tours)
            break
    report_path = folder / 'export-bericht.json'
    temporary_report = report_path.with_suffix('.json.part')
    temporary_report.write_text(json.dumps({'summary': result, 'tours': report}, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary_report.replace(report_path)
    return result
