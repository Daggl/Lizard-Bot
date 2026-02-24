Local UI (PySide6) — Quick Start

Prerequisites
- Python 3.10+ installed
- PySide6 available (install globally or in a venv)

Environment
- `CONTROL_API_TOKEN` — shared secret for the control API (set same value for bot and UI)
- `LOCAL_UI_ENABLE=1` — set before starting the bot so the control API is started

Run the bot (in one terminal):
```powershell
$env:CONTROL_API_TOKEN='your-token'
$env:LOCAL_UI_ENABLE='1'
python -m src.mybot
```

Run the UI (other terminal):
```powershell
$env:CONTROL_API_TOKEN='your-token'
python local_ui\app.py
```

Features
- Status polling (every 3s)
- Ping
- Reload Cogs (reloads `mybot.cogs.*` modules and calls their `setup()` if present)
- Shutdown bot

Security
- Keep `CONTROL_API_TOKEN` secret. The UI sends it from the environment when present.
- For higher security consider using a local-only Unix socket, HMAC, or client certs.
# Local UI

This is a simple native desktop UI for the bot. It communicates with the bot
via a local JSON-over-TCP control API (127.0.0.1:8765). To enable the API,
start the bot with the environment variable `LOCAL_UI_ENABLE=1`.

Quick start (Windows PowerShell):

```powershell
python -m src.mybot  # in one terminal, with LOCAL_UI_ENABLE=1
# in another terminal
python local_ui/app.py
```
