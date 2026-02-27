# Docs Index

Quick navigation for operations, structure and configuration.

## Getting Started

- Project entry point: [../README.md](../README.md)
- Local UI: [../local_ui/README.md](../local_ui/README.md)
- Web dashboard: [../web/README.md](../web/README.md)
- Docker: [../docker/DOCKER.md](../docker/DOCKER.md)
- Operations / Runbook: [operations.md](operations.md)

## Runtime Data

- Configuration: `config/*.json`
- Runtime data: `data/`
- Logs / tracing: `data/logs/`
- Log database: `data/db/logs.db`
- Poll data: `data/polls.json`

## Runtime Architecture

- Bot runtime: `src/mybot/runtime/`
- Legacy import wrappers: `src/mybot/lizard.py`, `src/mybot/control_api.py`
- i18n locale files: `data/locales/` (`en.json`, `de.json`)

## Dev Helpers

- Debug / utility scripts: [../scripts/dev/README.md](../scripts/dev/README.md)
