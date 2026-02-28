# Local UI

Native desktop UI (PySide6) for controlling the bot over local JSON-over-TCP API.

## Requirements

- Python 3.12+
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
- Birthday message editing and save flow
- Purge UI: delete user messages across channels with live progress

## Modules

- [app.py](app.py) — MainWindow wiring and startup orchestration
- [ui](ui) — tab builders, setup wizard, dialogs
- [controllers](controllers) — feature/controller mixins for UI actions
- [services](services) — control API client, log poller/formatting, helpers
- [config](config) — config I/O and editor helpers
- [core](core) — runtime bootstrap, repo paths, exception/startup hooks

## Notes

- `CONTROL_API_TOKEN` must match between bot and UI.
- `UI_TEST_MEMBER_NAME` can be set to control which user is preferred for UI event tests (default: `leutnantbrause`).
- Voice event tests (`/testmusic`) require voice dependencies in the bot environment (notably `PyNaCl`).
- Runtime trace/log output is written to [../data/logs](../data/logs).
- Dev helper scripts are in [../scripts/dev](../scripts/dev).

## Debug Mode

To enable additional UI-side debug logging (for handled exceptions and lifecycle paths), set `UI_DEBUG=1` before starting the UI.

PowerShell example:

```powershell
$env:UI_DEBUG='1'
.\.venv\Scripts\python local_ui\app.py
```

Debug output is written to [../data/logs/ui_debug.log](../data/logs/ui_debug.log).
