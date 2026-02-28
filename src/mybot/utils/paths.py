"""Repository path resolution and runtime directory/database bootstrapping."""

import os
import shutil
import sqlite3


def repo_root_candidates(path: str):
    """Yield parent directories from *path* up to the filesystem root."""
    p = os.path.abspath(path)
    parts = p.split(os.sep)
    for i in range(len(parts), 0, -1):
        yield os.sep.join(parts[:i])


def find_repo_root() -> str:
    """Locate the project root by searching for ``data/config.example.json``."""
    env_root = os.environ.get("DC_BOT_REPO_ROOT")
    if env_root:
        try:
            abs_env = os.path.abspath(env_root)
            if os.path.exists(os.path.join(abs_env, "data", "config.example.json")):
                return abs_env
        except Exception:
            pass

    here = os.path.abspath(os.path.dirname(__file__))
    # package path: src/mybot/utils -> climb up 3 levels
    cand = os.path.abspath(os.path.join(here, "..", "..", ".."))
    if os.path.exists(os.path.join(cand, "data", "config.example.json")):
        return cand

    # fallback: climb until we find a strong repo marker
    for c in repo_root_candidates(here):
        if os.path.exists(os.path.join(c, "data", "config.example.json")) or os.path.exists(
            os.path.join(c, "setup.cfg")
        ):
            return c
    return cand


REPO_ROOT = find_repo_root()

DATA_DIR = os.path.join(REPO_ROOT, "data")
DB_DIR = os.path.join(DATA_DIR, "db")
TICKETS_DIR = os.path.join(DATA_DIR, "tickets")
TICKET_TRANSCRIPTS = os.path.join(TICKETS_DIR, "transcripts")
LOGS_DIR = os.path.join(DATA_DIR, "logs")
CONFIG_DIR = os.path.join(REPO_ROOT, "config")
GUILDS_DIR = os.path.join(CONFIG_DIR, "guilds")


def guild_data_path(guild_id: int | str | None, filename: str) -> str:
    """Return the path to a guild-specific data file in config/guilds/{guild_id}/{filename}.
    
    If guild_id is None, returns empty string (no global fallback).
    Creates the guild directory if it doesn't exist.
    """
    if guild_id is None:
        return ""
    gid = str(guild_id)
    guild_dir = os.path.join(GUILDS_DIR, gid)
    os.makedirs(guild_dir, exist_ok=True)
    return os.path.join(guild_dir, filename)


def repo_path(*parts: str) -> str:
    """Join *parts* relative to the repository root."""
    return os.path.join(REPO_ROOT, *parts)


def ensure_dirs() -> None:
    """Create all required runtime directories."""
    os.makedirs(DB_DIR, exist_ok=True)
    os.makedirs(TICKETS_DIR, exist_ok=True)
    os.makedirs(TICKET_TRANSCRIPTS, exist_ok=True)
    os.makedirs(LOGS_DIR, exist_ok=True)


def get_db_path(name: str) -> str:
    """Return the path to ``data/db/<name>.db``, ensuring the directory exists."""
    ensure_dirs()
    return os.path.join(DB_DIR, f"{name}.db")


def ensure_runtime_storage() -> None:
    """Create directories and empty database files for logs, tickets and autorole."""
    ensure_dirs()
    for db_name in ("logs", "tickets", "autorole"):
        db_path = get_db_path(db_name)
        if os.path.exists(db_path):
            continue
        try:
            conn = sqlite3.connect(db_path)
            conn.close()
        except Exception:
            pass


def get_ticket_transcript_path(channel_id: int) -> str:
    """Return the file path for a ticket transcript by channel ID."""
    ensure_dirs()
    return os.path.join(TICKET_TRANSCRIPTS, f"{channel_id}.txt")


def migrate_old_paths() -> None:
    """Move legacy database files from old locations to the current layout."""
    ensure_dirs()
    old_logs = os.path.join(REPO_ROOT, "data", "logs", "logs.db")
    new_logs = get_db_path("logs")
    if os.path.exists(old_logs) and not os.path.exists(new_logs):
        try:
            shutil.move(old_logs, new_logs)
        except Exception:
            pass

    old_tickets = os.path.join(REPO_ROOT, "data", "logs", "tickets", "tickets.db")
    new_tickets = get_db_path("tickets")
    if os.path.exists(old_tickets) and not os.path.exists(new_tickets):
        try:
            shutil.move(old_tickets, new_tickets)
        except Exception:
            pass
