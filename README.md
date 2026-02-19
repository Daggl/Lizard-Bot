DC Bot
======

A Discord bot built by Leutnant Brause with discord.py. This repository contains modular cogs for moderation, leveling, tickets, logging and more. It uses SQLite for local persistence and provides a small CLI to query stored logs.

Quick start
-----------

1. Create a Python 3.11+ virtual environment and activate it.

Windows (PowerShell):
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the project root with your bot token:

```
DISCORD_TOKEN=your_token_here
```

4. (Optional) Set configuration constants inside `cogs/tickets/ticket.py`:
- `TICKET_CATEGORY_ID` — category where ticket channels will be created (channel ID integer)
- `SUPPORT_ROLE_ID` — role ID for staff/support who should see tickets
- `TICKET_LOG_CHANNEL_ID` — channel ID for logging ticket events

You may prefer to move these into a small central config file later. See the file header comments in `cogs/tickets/ticket.py` for guidance.

Run the bot
-----------

Start the bot from the project root:

```powershell
python bot.py
```

Start scripts
-------------

Two convenience scripts are included in the project root. They will create a `.venv` (if missing), activate it, install `requirements.txt` (if present) and start the bot.

- PowerShell (`start.ps1`):

```powershell
# run in foreground
.\start.ps1
```markdown
# DC Bot — Beginner Guide

This is a Discord bot (built with discord.py) that provides moderation, leveling, tickets, logging and small admin tools. The project stores data locally (SQLite) and includes helper scripts for starting the bot.

This README shows a minimal, step-by-step setup for beginners.

Prerequisites
-------------
- Python 3.10 or newer installed. Download from https://www.python.org if needed.
- A Discord bot token (create a bot at https://discord.com/developers/applications).

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

4) Provide your bot token
-------------------------
Create a file named `.env` in the project root with this single line:

```
DISCORD_TOKEN=your_bot_token_here
```

5) Start the bot
----------------
Simple foreground start (good for debugging):

```powershell
python bot.py
```

Convenience PowerShell script (creates/activates `.venv` and installs requirements automatically):

```powershell
.\start.ps1         # foreground
.\start.ps1 -Detach # background
```

What the project layout contains
--------------------------------
- `bot.py` — main runner.
- `src/mybot/` — packaged bot code (cogs and utils).
- `data/` — databases, logs and ticket transcripts (created at runtime).
- `config/` — per-cog JSON settings (the bot auto-generates missing files from `config.example.json`).
- `tools/` — small helper scripts (e.g., log query CLI).

Quick tests after start
-----------------------
- In any server where your bot is invited, try `*ping` to check the bot responds.
- Check `discord.log` in the project root if the bot exits or shows errors.

Common problems & fixes
-----------------------
- "DISCORD_TOKEN not set": Create `.env` with the token.
- Import errors: Ensure you activated the `.venv` and ran `pip install -r requirements.txt`.
- Permission errors writing `data/`: Give the running user write permissions to the project folder.

If you want me to: I can run the bot, tail logs for you, or add step-by-step screenshots to this README.

```
