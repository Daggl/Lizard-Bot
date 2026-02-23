FastAPI backend for the Bot Dashboard

This is a minimal scaffold for the dashboard backend.

Run (development):

```bash
python -m uvicorn main:app --reload --port 8000
```

Environment variables (optional):
- `WEB_INTERNAL_TOKEN` — a simple token protecting internal endpoints used by the bot.

Endpoints:
- `GET /api/ping`
- `GET /api/guilds/{guild_id}/config`
- `POST /api/guilds/{guild_id}/config` (requires `X-INTERNAL-TOKEN` header matching `WEB_INTERNAL_TOKEN` if set)
- `POST /api/guilds/{guild_id}/upload` (file upload)

OAuth placeholders exist in `/auth/*`.
