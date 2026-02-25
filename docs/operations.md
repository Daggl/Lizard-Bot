# Operations

Laufende Betriebsnotizen für lokale Runtime-Dateien.

## Logs

- UI schreibt Laufzeit-Tracking nach `data/logs/tracked.log`.
- `tracked.log` rotiert automatisch bei ca. 2 MB.
- Es werden maximal die letzten 5 Rotationsdateien (`tracked.log.bak.*`) behalten.

## Welcome Config Backups

- Beim Speichern von `config/welcome.json` wird eine Backup-Datei erzeugt.
- Es werden automatisch nur die letzten 5 Backups (`welcome.json.bak.*`) behalten.

## Runtime-Artefakte

- Temporäre Traces und Debug-Logs gehören nach `data/logs/`.
- Debug-/Maintenance-Skripte liegen unter `scripts/dev/`.
