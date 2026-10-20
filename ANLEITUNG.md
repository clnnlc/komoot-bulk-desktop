# Komoot Bulk – GPX Export

1. `KomootBulk.exe` starten (Windows 64 Bit, kein Python erforderlich).
2. E-Mail und Passwort deines eigenen Komoot-Kontos eingeben.
3. Einen Zielordner auswählen und **Alle Touren herunterladen** drücken.

Die App lädt alle abgeschlossenen Aktivitäten deines Kontos, einschließlich privater Touren, soweit Komoot den Zugriff erlaubt. Geplante Routen werden ausgeschlossen. Jede Aktivität wird als `tour-ID.gpx` gespeichert; der Tourname steht im GPX und in `export-bericht.json`. Die stabilen Dateinamen verhindern doppelte Downloads bei umbenannten Touren. Fotos und Highlight-POIs werden nicht exportiert.

Gültige vorhandene Dateien werden übersprungen. Fehlerhafte Downloads kannst du durch einen erneuten Lauf wiederholen. Zum erneuten Export einer bereits vorhandenen, später geänderten Tour ihre GPX-Datei aus dem Zielordner verschieben. Der Bericht zeigt die Ergebnisse des letzten Laufs. Ein Abbruch kann bis zum Ablauf der laufenden Netzwerkanfrage dauern.

Passwort und Sitzungstoken bleiben nur im Arbeitsspeicher. Sie werden weder in einer Konfigurationsdatei noch als Kommandozeilenargument gespeichert. Die App verwendet die E-Mail/Passwort-Anmeldung aus KomootGPX; eine Anmeldung über Google/Apple wird hier nicht angeboten. Bei einem solchen Konto gegebenenfalls zuerst bei Komoot ein Kontopasswort einrichten.

Die App nutzt die inoffizielle Komoot-Anbindung des Originalprojekts. Änderungen bei Komoot können Anpassungen erfordern. Automatisierte Tests prüfen Filterung, Seitenabruf, GPX-Erzeugung, Wiederaufnahme, Fehler und Abbruch mit Testdaten. Ein echter Kontoexport wurde ohne deine Zugangsdaten nicht getestet.

## Quellcode und Lizenz

Basiert auf https://github.com/timschneeb/KomootGPX von Tim Schneeberger und weiteren Mitwirkenden, Stand `b6e819b6b7717c334409bc342161aa15f5280463`.

App und mitgelieferter KomootGPX-Code: GPL-3.0, siehe `LICENSE`. Vollständiger App-Quellcode in `source/`. Die ursprünglichen Module liegen in `source/vendor/komootgpx`; ausschließlich deren `__init__.py` wurde angepasst, damit der CLI-Credential-Cache nicht initialisiert wird. Die Desktop-Anpassungen liegen in `exporter.py` und `app.py`. Änderungen vom 20.10.2026.

## Selbst bauen

Mit Python 3.12 auf Windows im Verzeichnis dieses Dokuments:

```powershell
python -m venv .venv
.venv/Scripts/python -m pip install -r source/requirements.txt
.venv/Scripts/python -m unittest discover -s source -p test_export.py
.venv/Scripts/python -m PyInstaller --noconfirm --clean --onefile --windowed --name KomootBulk --icon source/assets/app.ico --add-data "source/assets;assets" source/app.py
```

Die neue EXE liegt anschließend unter `dist/`. Alternativ mit `.venv/Scripts/python source/app.py` starten.

