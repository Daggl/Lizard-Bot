# Changelog

All notable changes to this project will be documented in this file.

## Unreleased

### Full Code Review (latest)

#### Critical Fixes
- **i18n persistence**: Language settings now persist to `data/language.json` instead of calling
  per-guild config without guild_id (which always returned empty)
- **Config cache clear**: `clear_cog_config_cache(name)` now correctly matches composite
  `"{guild_id}:{name}"` cache keys instead of bare name (which never matched)
- **Deleted stale `data/logs/database.py`**: Malformed duplicate of `data/logs/storage/database.py`

#### High-Priority Fixes
- **rewards.py**: Wrapped `add_roles` in try/except — `discord.Forbidden`/`HTTPException` no longer
  crashes the entire level-up flow
- **achievements.py**: Wrapped `channel.send` calls in try/except with fallback to `system_channel`
- **database.py**: Added `os.makedirs` before file write — fixes `FileNotFoundError` on new guilds
- **rank.py**: Moved XP sanitisation (`_to_int`) before text rendering (was rendering unsanitised values)
- **All 5 log cogs**: Fixed `_cfg()` to pass `guild.id` — per-guild log channels now work correctly
- **birthdays.py**: Normalise dates to zero-padded `DD.MM` format on save (fixes matching)
- **tempvoice.py**: Lock/Hide now read existing permission overwrites before modifying — no longer
  overwrite each other’s fields
- **welcome.py**: Channel/role IDs from JSON are now cast to `int()` (fixes `get_channel("123")` returning None)
- **levels.py**: Level-up messages now use `LEVEL_UP_CHANNEL_ID` (falls back to `ACHIEVEMENT_CHANNEL_ID`)
- **control_api.py**: `rank_preview` moved from standalone `if` (after `else`) to proper `elif` chain;
  fixed `_DummyMember` not assigned to variable; removed unused `peer` variable

#### Medium Fixes
- **tracking.py**: Cooldowns dict now pruned every 60s (entries older than 5 min) — fixes memory leak
- **level_config.py**: Sensible defaults when not configured: XP_PER_MESSAGE=15, MESSAGE_COOLDOWN=60s,
  VOICE_XP_PER_MINUTE=5
- **rank.py**: `addxp`/`removexp` commands now reject negative amounts
- **poll.py**: Only poll creator or moderators (manage_messages) can close a poll; duration capped
  at 7 days, minimum 10 seconds; `creator_id` stored in poll data
- **ticket.py**: `_cfg_opt_int` now receives `guild_id` for support role, category and log channel
- **music.py**: `_play_next` guards `get_guild()` returning None
- **admin_panel.py**: Soft import for leveling dependency (graceful fallback if leveling cog missing)
- **purge.py**: `discord.NotFound` no longer inflates delete count

#### Dead Code & Cleanup
- Deleted `src/mybot/cogs/leveling/utils/rank_card.py` (entire file unused, replaced by `rank.py`)
- Deleted `scripts/create_configs.py` (created global configs only, system uses per-guild)
- Deleted `config/guilds/*/rank.json.bak` backup files
- Removed unused `os` import from `birthdays.py`

#### Documentation
- Updated `docs/operations.md` with per-guild config paths and leveling defaults
- Updated `CONTRIBUTING.md` with per-guild config structure
- Updated `docs/README.md` with correct data/config paths
- Updated `local_ui/README.md` Python version (3.12+) and added purge feature

### Code Review & Refactoring

- **Critical fix**: Birthday date validation — rejects malformed DD.MM input
- **Critical fix**: Poll timeout — added missing `asyncio.TimeoutError` handler for duration prompt
- **Critical fix**: Autorole SQLite — converted all connections to `with` context managers (prevents connection leaks)
- **Critical fix**: Config store — temp file cleanup on failure (prevents disk leaks)
- **Bug fix**: Admin panel uptime — fixed >24h wrapping (time.strftime → custom `_format_uptime` with day support)
- **Bug fix**: Admin tools — removed duplicate `testachievement` command (was identical to `giveachievement`)
- **Deprecated API**: Replaced all `datetime.utcnow()` with `datetime.now(timezone.utc)` across 12 files
- **Logging**: Replaced `print()` debug statements with `logging` in autorole, ticket, levels cogs
- **Logging**: Cleaned up diagnostic logging in control API client, runtime controller, dashboard controller
- **i18n**: Fixed mixed German/English strings in voice_log (`"📤 Von"` → `"📤 From"`) and welcome cog debug output
- **i18n**: Translated all German UI strings in dashboard controller to English
- **Atomicity**: Converted `jsonstore.safe_save_json` to atomic writes (tempfile + rename pattern)
- **Performance**: Added `break` on first failed requirement check in achievements cog
- **Robustness**: Used `REPO_ROOT` import instead of fragile 5-level `os.path.dirname` chain in welcome cog
- **Docstrings**: Added module docstrings to 20+ files (cogs, utils, controllers, services)
- **Type hints**: Modernised `typing.Dict` / `Optional` → Python 3.10+ built-in generics in i18n module
- **Documentation**: Translated CONTRIBUTING.md, docs/README.md, operations.md from German to English
- **Documentation**: Added i18n and code-style sections to CONTRIBUTING.md

### Previous (Unreleased)

- Security: upgraded vulnerable dependencies to resolve multipart/form-data and h11/httpcore issues:
  - `fastapi` -> 0.132.0
  - `starlette` -> 0.52.1
  - `python-multipart` -> 0.0.22
  - `h11` -> 0.16.0
  - `httpx` -> 0.28.1
  - `httpcore` -> 1.0.9

  Rationale: `pip-audit` flagged ReDoS and multipart-related DoS vulnerabilities in older FastAPI/Starlette/multipart stacks. Upgrading removes known advisories; `pip-audit` reports no remaining known vulnerabilities after the upgrade.

  Notes & testing:
  - `pip-audit` run: `pip_audit_post_upgrade.json` (committed to the branch) — no advisories reported after upgrades.
  - API smoke tests executed: `/api/ping`, `/api/fonts`, `/api/guilds/123/config` — all returned expected responses.
  - Confirmed imports and local smoke tests; added CI workflow to run lint/tests/audit.

  Risk/Action items:
  - `httpcore` / `h11` compatibility required upgrading `httpx`/`httpcore`. This can surface runtime incompatibilities in HTTP streaming code — please run full integration tests and CI before merging.
  - FastAPI upgrade requires Pydantic v2 (already upgraded); review code for any Pydantic v1 → v2 API changes.

## 0.1.0 - (previous changes)
- Initial project scaffold and earlier changes (see git history).
