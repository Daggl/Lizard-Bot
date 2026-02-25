# Local UI

Native desktop UI (PySide6) for controlling the bot over local JSON-over-TCP API.

## Requirements

- Python 3.10+
- Dependencies from [requirements.txt](requirements.txt)
- Bot started with `LOCAL_UI_ENABLE=1`

## Start

Bot terminal:

```powershell
$env:CONTROL_API_TOKEN='your-token'
$env:LOCAL_UI_ENABLE='1'
.\.venv\Scripts\python -m src.mybot
```

UI terminal:

```powershell
$env:CONTROL_API_TOKEN='your-token'
.\.venv\Scripts\python local_ui\app.py
```

## Features

- Bot status, ping, reload, shutdown
- Welcome banner preview and save flow
- Rankcard preview and config save
- Live log tailing (file + sqlite mode)

## Notes

- `CONTROL_API_TOKEN` must match between bot and UI.
- Runtime trace/log output is written to [../data/logs](../data/logs).
- Dev helper scripts are in [../scripts/dev](../scripts/dev).
