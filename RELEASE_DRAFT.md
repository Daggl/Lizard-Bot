# Release v0.2.0 (Draft)

Release date: 2026-02-24

## Highlights

- Security upgrades: FastAPI/Starlette/python-multipart/h11/httpx/httpcore pinned to non-vulnerable versions.

## Details

See `CHANGELOG.md` for full notes. This release includes:

- `fastapi` -> 0.132.0
- `starlette` -> 0.52.1
- `python-multipart` -> 0.0.22
- `h11` -> 0.16.0
- `httpx` -> 0.28.1
- `httpcore` -> 1.0.9

## Testing performed

- Local smoke tests: `/api/ping`, `/api/fonts`, `/api/guilds/123/config` responded as expected.
- `pip-audit` run saved to `pip_audit_post_upgrade.json`.
- Docker images built successfully in CI.

## Post-release actions

- Observe logs for runtime issues related to `httpx`/`httpcore` streaming.
- Run broader integration tests in staging.
- Create GitHub Release from this draft and attach `pip_audit_post_upgrade.json`.
