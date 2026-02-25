# DC Bot

Discord bot with modular cogs, local desktop UI, and optional web dashboard.

## Quick Start (Bot only)

1. Create and activate virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install dependencies

```powershell
pip install -r requirements.txt
```

3. Create `.env` in project root

```env
DISCORD_TOKEN=your_bot_token_here
```

4. Start bot

```powershell
.\.venv\Scripts\python -m src.mybot
```

## Full Local Setup (Bot + Web)

Backend:

```powershell
.\.venv\Scripts\python -m uvicorn web.backend.main:app --host 127.0.0.1 --port 8000
```

Frontend:

```powershell
npm --prefix web/frontend install
npm --prefix web/frontend run dev
```

Bot:

```powershell
.\.venv\Scripts\python -m src.mybot
```

## Local UI (Desktop)

Run bot with control API enabled:

```powershell
$env:LOCAL_UI_ENABLE='1'
$env:CONTROL_API_TOKEN='your-token'
.\.venv\Scripts\python -m src.mybot
```

Run UI in another terminal:

```powershell
$env:CONTROL_API_TOKEN='your-token'
.\.venv\Scripts\python local_ui\app.py
```

See detailed UI notes in [local_ui/README.md](local_ui/README.md).

## Project Structure

- [src/mybot](src/mybot): bot package, cogs, control API
- [local_ui](local_ui): PySide6 desktop UI
- [web](web): dashboard backend + frontend (see [web/README.md](web/README.md))
- [config](config): per-cog runtime configuration
- [data](data): runtime data, logs, uploads
- [scripts](scripts): maintenance and dev helper scripts

## Related Docs

- [docs/README.md](docs/README.md)
- [CONTRIBUTING.md](CONTRIBUTING.md)
- [web/README.md](web/README.md)
- [web/backend/README.md](web/backend/README.md)
- [web/frontend/README.md](web/frontend/README.md)
- [docker/DOCKER.md](docker/DOCKER.md)
