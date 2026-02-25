# Contributing

Kurze Regeln, damit das Repository aufgeräumt bleibt.

## Struktur

- Produktivcode bleibt in `src/`, `local_ui/`, `web/`.
- Runtime-Dateien gehören nach `data/` (nicht ins Root).
- Lokale Debug-Utilities gehören nach `scripts/dev/`.

## Konfiguration & Daten

- Persistente Bot-Settings liegen in `config/*.json`.
- Runtime-Backups (`*.bak.*`) nicht committen.
- Einheitliche Dateinamen in `data/` nutzen (lowercase, z. B. `polls.json`).

## Logging

- Laufzeitlogs und Traces liegen unter `data/logs/`.
- Keine temporären Trace-Dateien im Projekt-Root.

## Dokumentation

- Root-README bleibt Einstiegspunkt.
- Bereichsdokus liegen bei den Modulen (`local_ui/README.md`, `web/README.md`).
- Neue Tools/Skripte immer kurz in passender README dokumentieren.

## PR-Hinweise

- Kleine, thematisch fokussierte Änderungen.
- Keine Misch-PRs aus Feature + Refactor + Formatierung.
- Vor Übergabe mindestens Syntax/Start-Check für geänderte Komponenten.
