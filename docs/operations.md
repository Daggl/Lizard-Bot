# Operations

Runtime operations notes for managing local runtime files.

## Logs

- UI writes runtime tracking to `data/logs/tracked.log`.
- `tracked.log` auto-rotates at ~2 MB.
- Only the last 5 rotation files (`tracked.log.bak.*`) are kept.

## Welcome Config Backups

- Saving `config/welcome.json` creates a backup file.
- Only the last 5 backups (`welcome.json.bak.*`) are retained automatically.

## Runtime Artefacts

- Temporary traces and debug logs go into `data/logs/`.
- SQLite log database is at `data/db/logs.db`.
- Debug / maintenance scripts are in `scripts/dev/`.

## Runtime Modules

- Bot runtime code lives under `src/mybot/runtime/` (`lizard.py`, `control_api.py`).
- Top-level modules in `src/mybot/` are compatibility wrappers (re-exports).

## UI Event Tests

- By default, the username `leutnantbrause` is preferred for event tests.
- Set `UI_TEST_MEMBER_NAME` to override the preferred test user.
