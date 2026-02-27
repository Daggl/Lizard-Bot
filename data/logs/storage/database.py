import json
import os
import sqlite3
from datetime import datetime, timezone

from mybot.utils.paths import ensure_dirs, get_db_path, migrate_old_paths

# migrate old files if present, ensure new dirs
try:
    migrate_old_paths()
except Exception:
    pass

DB_PATH = get_db_path("logs")


def connect():
    ensure_dirs()
    return sqlite3.connect(DB_PATH)


def setup():
    con = connect()
    cur = con.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT,
        type TEXT,
        user_id INTEGER,
        user_name TEXT,
        moderator_id INTEGER,
        moderator_name TEXT,
        channel_id INTEGER,
        channel_name TEXT,
        message TEXT,
        extra TEXT,
        timestamp TEXT
    )
    """)

    # Backward-compatible migrations for older DBs
    cur.execute("PRAGMA table_info(logs)")
    existing_cols = {row[1] for row in cur.fetchall()}
    if "user_name" not in existing_cols:
        cur.execute("ALTER TABLE logs ADD COLUMN user_name TEXT")
    if "moderator_name" not in existing_cols:
        cur.execute("ALTER TABLE logs ADD COLUMN moderator_name TEXT")
    if "channel_name" not in existing_cols:
        cur.execute("ALTER TABLE logs ADD COLUMN channel_name TEXT")

    cur.execute("CREATE INDEX IF NOT EXISTS idx_logs_category ON logs(category)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_logs_type ON logs(type)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON logs(timestamp)")

    con.commit()
    con.close()


def _pick_int(data, *keys):
    for key in keys:
        try:
            val = data.get(key)
            if val is None:
                continue
            return int(val)
        except Exception:
            continue
    return None


def _pick_str(data, *keys):
    for key in keys:
        try:
            val = data.get(key)
            if val is None:
                continue
            text = str(val)
            if text:
                return text
        except Exception:
            continue
    return None


def save_log(category, data):
    data = data or {}

    user_id = _pick_int(data, "user", "user_id")
    user_name = _pick_str(data, "user_name", "username", "member_name")
    moderator_id = _pick_int(data, "by", "moderator_id", "deleted_by", "closed_by", "claimed_by")
    moderator_name = _pick_str(data, "by_name", "moderator_name", "deleted_by_name", "closed_by_name", "claimed_by_name")
    channel_id = _pick_int(data, "channel", "channel_id", "to", "from")
    channel_name = _pick_str(data, "channel_name", "to_name", "from_name")
    log_type = _pick_str(data, "type") or "event"
    message = _pick_str(data, "message", "content", "before", "after", "reason")
    timestamp = _pick_str(data, "timestamp", "created_at") or datetime.now(timezone.utc).isoformat()

    try:
        extra = json.dumps(data, ensure_ascii=False, sort_keys=True)
    except Exception:
        extra = str(data)

    con = connect()
    cur = con.cursor()

    cur.execute(
        """
        INSERT INTO logs
        (category, type, user_id, user_name, moderator_id, moderator_name, channel_id, channel_name, message, extra, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            category,
            log_type,
            user_id,
            user_name,
            moderator_id,
            moderator_name,
            channel_id,
            channel_name,
            message,
            extra,
            timestamp,
        ),
    )

    con.commit()
    con.close()


setup()
