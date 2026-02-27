# Changelog

All notable changes to this project will be documented in this file.

## Unreleased

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
