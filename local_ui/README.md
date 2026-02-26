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
- Rank preview and config save
- Live log tailing (file + sqlite mode)

## Modules

- [app.py](app.py) — MainWindow UI composition and event handlers
- [runtime.py](runtime.py) — app bootstrap, single-instance lock, optional event tracing
- [control_api_client.py](control_api_client.py) — control API request helper (`send_cmd`)
- [log_poller.py](log_poller.py) — background polling thread for file/sqlite logs
- [log_format.py](log_format.py) — sqlite row formatter for readable log output
- [guides.py](guides.py) — tutorial and commands dialogs/content
- [config_editor.py](config_editor.py) — JSON config editor dialog
- [config_io.py](config_io.py) — shared config JSON path/load/save helpers
- [file_ops.py](file_ops.py) — backup pruning, log rotation, tracked writer helpers
- [exception_handler.py](exception_handler.py) — global UI exception hook
- [startup_trace.py](startup_trace.py) — startup trace marker writer

## Notes

- `CONTROL_API_TOKEN` must match between bot and UI.
- Runtime trace/log output is written to [../data/logs](../data/logs).
- Dev helper scripts are in [../scripts/dev](../scripts/dev).
