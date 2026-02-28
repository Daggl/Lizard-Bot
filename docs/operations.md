# Operations

Runtime operations notes for managing local runtime files.

## Per-Guild Configuration

- All bot settings are **per-guild** and stored under `config/guilds/{guild_id}/`.
- Each config file (e.g. `welcome.json`, `leveling.json`, `rank.json`) is loaded
  per guild — there is **no global** config fallback.
- Language settings are stored globally in `data/language.json`.
- The UI creates guild config files when a guild is selected.

## Logs

- UI writes runtime tracking to `data/logs/tracked.log`.
- `tracked.log` auto-rotates at ~2 MB.
- Only the last 5 rotation files (`tracked.log.bak.*`) are kept.

## Welcome Config Backups

- Saving welcome config creates per-guild backup files.
- Only the last 5 backups (`*.bak.*`) are retained automatically.

## Runtime Artefacts

- Temporary traces and debug logs go into `data/logs/`.
- SQLite log database is at `data/db/logs.db`.
- Debug / maintenance scripts are in `scripts/dev/`.

## Runtime Modules

- Bot runtime code lives under `src/mybot/runtime/` (`lizard.py`, `control_api.py`).
- Top-level modules in `src/mybot/` are compatibility wrappers (re-exports).

## Leveling Defaults

- When leveling config is not set for a guild, sensible defaults apply:
  - `XP_PER_MESSAGE`: 15
  - `MESSAGE_COOLDOWN`: 60 seconds
  - `VOICE_XP_PER_MINUTE`: 5
  - `LEVEL_BASE_XP`: 100
  - `LEVEL_XP_STEP`: 50
- `LEVEL_UP_CHANNEL_ID` can be set separately from `ACHIEVEMENT_CHANNEL_ID`.
  If not set, it falls back to the achievement channel.

## UI Event Tests

- By default, the username `leutnantbrause` is preferred for event tests.
- Set `UI_TEST_MEMBER_NAME` to override the preferred test user.
