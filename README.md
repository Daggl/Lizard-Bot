```markdown
# Lizard Bot — Beginner Guide

Lizard Bot is a Discord bot (built with discord.py) that provides moderation, leveling, tickets, logging and admin helpers. This guide helps beginners set up and run the bot locally.

Prerequisites
-------------
- Python 3.10 or newer installed: https://www.python.org
- Node.js (for frontend development) if you plan to run the frontend locally: https://nodejs.org
- Docker (optional) if you plan to run the services in containers: https://www.docker.com
- A Discord bot token from the Discord Developer Portal: https://discord.com/developers/applications

1) Open a terminal (PowerShell on Windows)
---------------------------------------
On Windows press Start → type "PowerShell" → open it.

2) Create and activate a virtual environment (recommended)
---------------------------------------------------------
In the project folder run:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks script execution, run as Administrator once and execute:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

3) Install dependencies
-----------------------
With the virtual environment active:

```powershell
pip install -r requirements.txt
```

4) Provide your secrets and env vars
-----------------------------------
Create a file named `.env` in the project root containing the values below (example):

```
DISCORD_TOKEN=your_bot_token_here
# Optional (for Spotify import):
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
# Internal token used by the frontend/backend to authenticate preview/upload requests
WEB_INTERNAL_TOKEN=a-random-secret
```

Keep `.env` private and never commit it to the repository.

5) Start the bot and services
----------------------------
Recommended local development flow (create venv, install deps and run services).

Quick sequence (PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Run backend (uvicorn)
.\.venv\Scripts\python -m uvicorn web.backend.main:app --host 127.0.0.1 --port 8000

# In a second terminal: frontend dev server (if you want hot reload)
npm --prefix web/frontend install
npm --prefix web/frontend run dev

# In a third terminal: start the bot (needs DISCORD_TOKEN in .env)
.\.venv\Scripts\python -m src.mybot
```

Alternatively you can use the provided helpers which automate these steps:

- PowerShell (foreground): `.\start.ps1` (backend + frontend + bot)
- PowerShell (detached bot): `.\start.ps1 -Detach`
- Windows (cmd): `start.bat`

Or run the bot directly as a package:

```powershell
python -m src.mybot
```

Docker: a portable option is provided — see `DOCKER.md` and use:

```bash
docker compose up --build
```
This starts the `backend` (http://localhost:8000), `frontend` (http://localhost:5173) and the `bot` container.

Project layout (important files)
--------------------------------
- `src/mybot/` — packaged bot code (cogs and utils). This is the canonical bot code; run with `python -m src.mybot` or via the provided start scripts.
- `web/backend/` — FastAPI dashboard backend (endpoints, preview generation).
- `web/frontend/` — React + Vite dashboard frontend (development and production build).
- `data/` — runtime data, logs and uploads (created at runtime).
- `data/config.example.json` — example per-cog config. On first bot startup the repository-level example is used to create the per-cog files under `config/` if they are missing.
- `config/` — per-guild JSON settings (create by copying `data/config.example.json` here or let the bot create them automatically).
- `start.ps1`, `start.bat` — helper scripts to create a venv, start backend, frontend and the bot for local development.
- `docker-compose.yml`, `Dockerfile.python`, `Dockerfile.frontend` — containerized deployment artifacts (see `DOCKER.md`).

Music features
--------------
The bot includes a `music` cog which can play YouTube tracks and import Spotify tracks/playlists.

- Requirements: `ffmpeg` installed and available on `PATH`, and `yt-dlp` (added to `requirements.txt`).
- Spotify playlist/track import uses Spotify's Web API (Client Credentials). Provide credentials in `.env` as shown below.

Examples:

```powershell
# Play/search a YouTube track or search term (prefix commands)
*play Never Gonna Give You Up

# Play a YouTube URL
*play https://www.youtube.com/watch?v=dQw4w9WgXcQ

# Import a Spotify track or playlist into the queue (requires SPOTIFY_CLIENT_ID/SECRET)
*spotify https://open.spotify.com/playlist/xxxxx  # optional: max_tracks
```

Progress & cancel
------------------
When importing a Spotify playlist the bot posts a progress embed which is updated during import. The requester (and server admins) can cancel the import via the "Abbrechen" button.

Environment variables
---------------------
Add the following to `.env` in the project root (example values):

```
DISCORD_TOKEN=your_bot_token_here
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
```

Security note: keep `.env` private and never commit it to a public repository.

Quick smoke tests
-----------------
- After starting the bot, try `*ping` in a server where the bot is invited.
- Check `discord.log` in the project root for stack traces if the bot exits.
- Backend health: visit `http://localhost:8000/api/ping` — should return `{ "ok": true }`.
- Frontend: open `http://localhost:5173` (if running via `start` or Docker).

Troubleshooting
---------------
- "DISCORD_TOKEN not set": Create `.env` with the token in the project root.
- If the frontend fails to build or `npm` is missing, install Node.js and run `npm install` in `web/frontend`.
- If `uvicorn`/backend fails: ensure `requirements.txt` is installed into the active venv, or run the backend via Docker.
- If ports 8000 or 5173 are already in use, stop the conflicting process or adjust ports in `start` scripts and `docker-compose.yml`.
- Permission errors writing `data/`: Ensure the user running the bot has write permissions to the project folder.


If you want, I can run the bot, tail logs, or add screenshots to this README.

```
