## Summary

This PR upgrades several dependencies to address security advisories and dependency compatibility:

- `fastapi` -> 0.132.0
- `starlette` -> 0.52.1
- `python-multipart` -> 0.0.22
- `h11` -> 0.16.0
- `httpx` -> 0.28.1
- `httpcore` -> 1.0.9

These upgrades were applied in branch `chore/upgrade-httpcore-httpx`.

## Rationale

`pip-audit` reported ReDoS and multipart-related DoS vulnerabilities in older versions of FastAPI/Starlette/python-multipart and h11/request-smuggling advisories. Upgrading the listed packages removes the known advisories.

## What I tested

- `pip-audit` run (see `pip_audit_post_upgrade.json`) — no remaining advisories reported.
- Local API smoke tests: `/api/ping`, `/api/fonts`, `/api/guilds/123/config` — returned 200 as expected.
- Ran `scripts/import_all_src_mybot.py` — all `src.mybot` modules import cleanly.
- Added CI workflow `.github/workflows/ci.yml` to run flake8, pytest (if tests exist) and pip-audit on future PRs.

## Risks / Notes

- FastAPI upgrade requires Pydantic v2; the codebase now pins `pydantic` 2.x. Please review code paths that use Pydantic models for potential API differences.
- `httpcore`/`h11` compatibility required upgrading `httpx` and `httpcore`. This may affect low-level HTTP streaming behaviors; please run integration tests that exercise HTTP requests (e.g., dashboard endpoints, file uploads, music features using httpx/yt-dlp).

## Checklist

- [ ] Run full test suite / integration tests in CI
- [ ] Sanity-check bot runtime in staging environment
- [ ] Merge and monitor for any runtime regressions

If you'd like I can also open a follow-up PR to pin narrower version ranges or add compatibility shims.
