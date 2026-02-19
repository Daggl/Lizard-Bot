import os


def _repo_root():
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))


def ensure_dirs():
    root = _repo_root()
    os.makedirs(os.path.join(root, "data", "db"), exist_ok=True)
    os.makedirs(os.path.join(root, "data", "tickets", "transcripts"), exist_ok=True)
    os.makedirs(os.path.join(root, "config"), exist_ok=True)


def get_db_path(name: str) -> str:
    """Return path to data/db/<name>.db"""
    ensure_dirs()
    root = _repo_root()
    return os.path.join(root, "data", "db", f"{name}.db")


def get_ticket_transcript_path(channel_id: int) -> str:
    ensure_dirs()
    root = _repo_root()
    return os.path.join(root, "data", "tickets", "transcripts", f"{channel_id}.txt")


def migrate_old_paths():
    """Placeholder for migration logic (no-op)."""
    # Real migration handled elsewhere; keep function for compatibility.
    return
import os
import shutil


def repo_root_candidates(path):
    p = os.path.abspath(path)
    parts = p.split(os.sep)
    for i in range(len(parts), 0, -1):
        yield os.sep.join(parts[:i])


def find_repo_root():
    here = os.path.abspath(os.path.dirname(__file__))
    # package path: src/mybot/utils -> climb up 3 levels
    cand = os.path.abspath(os.path.join(here, "..", "..", ".."))
    if os.path.exists(os.path.join(cand, "bot.py")) or os.path.exists(os.path.join(cand, "config.example.json")):
        return cand
    # fallback: climb until we find bot.py
    for c in repo_root_candidates(here):
        if os.path.exists(os.path.join(c, "bot.py")) or os.path.exists(os.path.join(c, "config.example.json")):
            return c
    return cand


REPO_ROOT = find_repo_root()

DATA_DIR = os.path.join(REPO_ROOT, "data")
DB_DIR = os.path.join(DATA_DIR, "db")
TICKETS_DIR = os.path.join(DATA_DIR, "tickets")
TICKET_TRANSCRIPTS = os.path.join(TICKETS_DIR, "transcripts")
LOGS_DIR = os.path.join(DATA_DIR, "logs")


def ensure_dirs():
    os.makedirs(DB_DIR, exist_ok=True)
    os.makedirs(TICKETS_DIR, exist_ok=True)
    os.makedirs(TICKET_TRANSCRIPTS, exist_ok=True)
    os.makedirs(LOGS_DIR, exist_ok=True)


def get_db_path(name: str) -> str:
    ensure_dirs()
    return os.path.join(DB_DIR, f"{name}.db")


def get_ticket_transcript_path(channel_id: int) -> str:
    ensure_dirs()
    return os.path.join(TICKET_TRANSCRIPTS, f"{channel_id}.txt")


def migrate_old_paths():
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
