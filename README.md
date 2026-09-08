# Meetingraumverwaltung

Interne Web-App für die Verwaltung von Meetingräumen, Ausstattung, Buchungsregeln, Modernisierungen und Tickets. Die Daten werden in einer SQLite-Datenbank in einem Docker-Volume gespeichert.

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
docker volume create meetingroom-data
docker run -d --name meetingroom-app --restart unless-stopped \
  -p 8080:8080 \
  -v meetingroom-data:/app/data \
  ghcr.io/<GITHUB-ORGANISATION-ODER-BENUTZER>/<REPOSITORY>:latest
```

Danach ist die Anwendung unter `http://<IP-DER-VM>:8080` verfügbar. Die Daten verbleiben im Volume `meetingroom-data`, auch wenn der Container aktualisiert wird.

### Mit Docker Compose

Lege neben der `docker-compose.yml` eine Datei `.env` an:

```dotenv
MEETINGROOM_IMAGE=ghcr.io/<GITHUB-ORGANISATION-ODER-BENUTZER>/<REPOSITORY>:latest
MEETINGROOM_PORT=8080
```

Dann starten bzw. aktualisieren:

```bash
docker compose pull
docker compose up -d
```

Für einen lokalen Entwicklungs-Build kann das Image in der `.env` überschrieben oder `docker compose` um einen `build:`-Eintrag ergänzt werden.

## Ohne Docker

Python 3.11+:

```bash
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8080
```

Die Datenbank liegt in `data/meetingrooms.db`.

## Hinweis zur Sicherheit

Die App hat bewusst keinen Login. Sie sollte deshalb nur in einem internen, entsprechend abgeschotteten Netzwerk erreichbar sein und nicht direkt ins Internet veröffentlicht werden.
