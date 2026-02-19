```markdown
# Lizard Bot — Beginner Guide

Lizard Bot is a Discord bot (built with discord.py) that provides moderation, leveling, tickets, logging and admin helpers. This guide helps beginners set up and run the bot locally.

Prerequisites
-------------
- Python 3.10 or newer installed: https://www.python.org
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

4) Provide your bot token
-------------------------
Create a file named `.env` in the project root with this single line:

```
DISCORD_TOKEN=your_bot_token_here
```

5) Start the bot
----------------
Foreground (recommended while testing):

```powershell
python bot.py
```

Use the bundled PowerShell helper to create a venv and run the bot automatically:

```powershell
.\start.ps1         # foreground
.\start.ps1 -Detach # run in background
```

Project layout (important files)
--------------------------------
- `bot.py` — main entry point.
- `src/mybot/` — packaged bot code (cogs and utils).
- `data/` — databases, logs and ticket transcripts (created at runtime).
- `config/` — per-cog JSON settings (missing files are auto-generated from `config.example.json`).
- `tools/` — small helper scripts (e.g., `tools/query_logs.py`).

Quick smoke tests
-----------------
- After starting, try `*ping` in a server where the bot is invited.
- Check `discord.log` in the project root for stack traces if the bot exits.

Troubleshooting
---------------
- "DISCORD_TOKEN not set": Create `.env` with the token.
- Import errors: Make sure you activated the `.venv` and ran `pip install -r requirements.txt`.
- Permission errors writing `data/`: Ensure the user running the bot has write permissions to the project folder.

If you want, I can run the bot, tail logs, or add screenshots to this README.

```
