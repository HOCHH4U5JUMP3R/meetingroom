# Meetingraumverwaltung

Interne Web-App für die Verwaltung von Meetingräumen, Ausstattung, Buchungsregeln, Modernisierungen und Tickets. Die Daten werden in einer SQLite-Datenbank im persistent eingebundenen Verzeichnis `data/` gespeichert.

Die Startseite bietet eine durchsuchbare Übersicht aller Standorte und Räume. Ein Klick auf eine Raumkarte öffnet die vollständige Raumakte.

## Als GitHub Container Registry (GHCR) Paket bereitstellen

Der Workflow [`.github/workflows/publish-ghcr.yml`](.github/workflows/publish-ghcr.yml) baut bei einem Push auf `main`, bei einem `v*`-Tag oder manuell ein Container-Image und veröffentlicht es unter:

```text
ghcr.io/<GITHUB-ORGANISATION-ODER-BENUTZER>/<REPOSITORY>:latest
```

Damit das Paket außerhalb von GitHub genutzt werden kann, muss es in den Package-Einstellungen **public** sein. Für ein privates Paket zuerst auf der VM anmelden:

```bash
echo "$GITHUB_TOKEN" | docker login ghcr.io -u <GITHUB-BENUTZER> --password-stdin
```

## Auf der VM starten

Ohne Repository-Checkout kann die Anwendung direkt als Container gestartet werden. Ersetze den Platzhalter durch den tatsächlichen GHCR-Pfad:

```bash
mkdir -p data
docker run -d --name meetingroom-app --restart unless-stopped \
  -p 8080:8080 \
  -v "$(pwd)/data:/app/data" \
  ghcr.io/<GITHUB-ORGANISATION-ODER-BENUTZER>/<REPOSITORY>:latest
```

Danach ist die Anwendung unter `http://<IP-DER-VM>:8080` verfügbar. Die Daten verbleiben im Verzeichnis `data/`, auch wenn der Container aktualisiert wird.

### Mit Docker Compose

Lege neben der `docker-compose.yml` eine Datei `.env` an:

```dotenv
MEETINGROOM_IMAGE=ghcr.io/<GITHUB-ORGANISATION-ODER-BENUTZER>/<REPOSITORY>:latest
MEETINGROOM_PORT=8080
# Optional: abweichender Host-Pfad für die SQLite-Daten
MEETINGROOM_DATA_DIR=./data
```

Dann starten bzw. aktualisieren:

```bash
docker compose pull
docker compose up -d
```

Für einen lokalen Entwicklungs-Build kann das Image in der `.env` überschrieben oder `docker compose` um einen `build:`-Eintrag ergänzt werden.

### Vorherige Daten nach einer Version mit Docker-Volume wiederherstellen

Falls bereits die vorherige Compose-Version mit dem Volume `meetingroom-data` verwendet wurde, liegen die seitdem neu angelegten Räume dort. Diese Version bindet wieder `./data/` ein und macht damit die Daten aus der ursprünglichen Installation wieder verfügbar.

**Wichtig:** Kopiere nicht unbesehen beide SQLite-Dateien übereinander, da eine Datei die andere ersetzen würde. Falls das Volume die aktuelleren Daten enthält, sichere zuerst beide Varianten und kopiere anschließend bewusst die gewünschte Datenbank zurück:

```bash
mkdir -p backup data
docker run --rm -v meetingroom-data:/source:ro -v "$(pwd)/backup:/backup" \
  alpine sh -c 'cp /source/meetingrooms.db /backup/meetingrooms-from-volume.db'
cp data/meetingrooms.db backup/meetingrooms-from-host.db
# Nur falls die Volume-Version die gewünschte ist:
cp backup/meetingrooms-from-volume.db data/meetingrooms.db
```

Danach nutzt die Anwendung wieder dauerhaft `./data/`. Die beiden Sicherungskopien bleiben für eine manuelle Zusammenführung erhalten.

## Ohne Docker

Python 3.11+:

```bash
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8080
```

Die Datenbank liegt in `data/meetingrooms.db`.

## Hinweis zur Sicherheit

Die App hat bewusst keinen Login. Sie sollte deshalb nur in einem internen, entsprechend abgeschotteten Netzwerk erreichbar sein und nicht direkt ins Internet veröffentlicht werden.
