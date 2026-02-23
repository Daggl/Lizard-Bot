# Changelog

All notable changes to this project will be documented in this file.

## Unreleased

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
