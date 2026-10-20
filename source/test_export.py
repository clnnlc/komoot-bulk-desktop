import tempfile
import threading
import unittest
from unittest.mock import patch, Mock
import xml.etree.ElementTree as ET
from pathlib import Path
from exporter import export_tours, DesktopApi, render_gpx

class FakeApi:
    def fetch_tours(self, **kw):
        assert kw['tour_type'] == 'tour_recorded'
        return {'1': {'id': '1', 'type': 'tour_recorded'}, '2': {'id': '2', 'type': 'tour_planned'}, '3': {'id': '3', 'type': 'tour_recorded'}}
    def fetch_tour(self, tid, **kw):
        if tid == '3':
            raise ValueError('broken tour')
        return {'id': tid, 'type': 'tour_recorded'}

class ExportTests(unittest.TestCase):
    def test_upstream_pagination_and_recorded_filter(self):
        pages = [
            {'_links': {'next': {'href': 'https://api.komoot.de/page2'}}, '_embedded': {'tours': [{'id': '1', 'type': 'tour_planned'}]}},
            {'_links': {}, '_embedded': {'tours': [{'id': '2', 'type': 'tour_recorded'}]}}
        ]
        api = DesktopApi(threading.Event())
        api.user_id = '123'
        with patch('exporter.requests.get', side_effect=[Mock(status_code=200, json=lambda: pages[0]), Mock(status_code=200, json=lambda: pages[1])]) as get:
            self.assertEqual(list(api.fetch_tours('tour_recorded')), ['2'])
            self.assertEqual(get.call_count, 2)
            self.assertEqual(get.call_args.kwargs['timeout'], (10, 30))

    def test_actual_gpx_generator(self):
        tour = {'id': '123', 'name': 'Berg & Tal', 'type': 'tour_recorded', 'distance': 1000, 'duration': 600,
                'elevation_up': 50, 'elevation_down': 30, 'date': '2026-10-20T10:00:00.000+0000',
                '_embedded': {'creator': {'display_name': 'Test', 'username': '1'},
                              'coordinates': {'items': [{'lat': 48.1, 'lng': 11.2, 'alt': 500, 't': 0}, {'lat': 48.2, 'lng': 11.3, 't': 1000}]}}}
        root = ET.fromstring(render_gpx(tour, None))
        points = [e for e in root.iter() if e.tag.endswith('}trkpt')]
        self.assertEqual(len(points), 2)
        self.assertEqual(points[0].attrib['lat'], '48.1')

    def test_auth_failure_and_foreign_host(self):
        api = DesktopApi(threading.Event())
        with patch('exporter.requests.get', return_value=Mock(status_code=401)):
            with self.assertRaisesRegex(RuntimeError, 'Anmeldung'):
                api.login('test@example.com', 'test')
        with patch('exporter.requests.get') as get:
            with self.assertRaises(RuntimeError):
                api._KomootApi__send_request('https://example.com', None)
            get.assert_not_called()

    def test_filter_resume_and_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            events = []
            render = lambda tour, api: '<gpx><trk><trkseg><trkpt lat="1" lon="2"/></trkseg></trk></gpx>'
            args = (FakeApi(), Path(folder), threading.Event(), lambda *e: events.append(e))
            result = export_tours(*args, render=render)
            self.assertEqual(result, {'saved': 1, 'skipped': 0, 'failed': 1, 'cancelled': False})
            self.assertFalse((Path(folder) / 'tour-2.gpx').exists())
            result = export_tours(*args, render=render)
            self.assertEqual(result['skipped'], 1)
            (Path(folder) / 'tour-1.gpx').write_text('incomplete')
            self.assertEqual(export_tours(*args, render=render)['saved'], 1)
    def test_cancel(self):
        with tempfile.TemporaryDirectory() as folder:
            stop = threading.Event()
            stop.set()
            result = export_tours(FakeApi(), Path(folder), stop, lambda *e: None)
            self.assertTrue(result['cancelled'])
            self.assertEqual(list(Path(folder).glob('*.gpx')), [])

if __name__ == '__main__':
    unittest.main()
