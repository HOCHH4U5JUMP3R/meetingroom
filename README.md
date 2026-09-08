# Meetingraumverwaltung

Interne Web-App für die Verwaltung von Meetingräumen.

## Funktionen
- Raum auswählen und komplette Raumakte anzeigen
- Stammdaten und Raumverantwortlicher
- Ausstattung pro Raum verwalten
- Buchungsberechtigungen und Genehmiger dokumentieren
- Modernisierungen planen und Budget/Beauftragung/Ist-Kosten verwalten
- Tickets und Fehlerhistorie pro Raum
- Gesamtbudget-Dashboard
- SQLite-Datenbank, kein Login
- Docker/VirtualBox-freundlich

## Start mit Docker

```bash
docker compose up -d --build
```

Dann im Browser:
`http://<IP-DER-VM>:8080`

## Ohne Docker

Python 3.11+:
```bash
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8080
```

Die Datenbank liegt in `data/meetingrooms.db`.

## Hinweis zur Sicherheit
Die App hat bewusst keinen Login. Sie sollte deshalb nur in einem internen, entsprechend abgeschotteten Netzwerk erreichbar sein. Nicht direkt ins Internet veröffentlichen.
