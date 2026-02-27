# Contributing

Short rules to keep the repository clean and consistent.

## Structure

- Production code stays in `src/`, `local_ui/`, `web/`.
- Runtime data goes in `data/` (not the project root).
- Local debug utilities go in `scripts/dev/`.

## Configuration & Data

- Persistent bot settings live in `config/*.json`.
- Runtime backups (`*.bak.*`) should not be committed.
- Use consistent file names in `data/` (lowercase, e.g. `polls.json`).

## Logging

- Runtime logs and traces live under `data/logs/`.
- No temporary trace files in the project root.
- Use `logging` (Python stdlib) instead of `print()` for runtime output.

## Internationalisation (i18n)

- All user-facing bot strings should use the `translate` / `translate_for_ctx` helpers from `mybot.utils.i18n`.
- Locale files are in `data/locales/` (`en.json`, `de.json`).
- Internal log messages and code comments should be in English.

## Documentation

- Root README is the entry point.
- Module-specific docs sit next to their code (`local_ui/README.md`, `web/README.md`).
- New tools or scripts should always be briefly documented in the relevant README.

## Code Style

- Use `datetime.now(timezone.utc)` instead of the deprecated `datetime.utcnow()`.
- Prefer `with` context managers for SQLite connections.
- Add module and class docstrings to all new files.

## PR Guidelines

- Small, focused changes per PR.
- No mixed PRs combining features + refactoring + formatting.
- Run at least a syntax/startup check for changed components before submitting.
