import os
import sqlite3
from datetime import datetime

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
        moderator_id INTEGER,
        channel_id INTEGER,
        message TEXT,
        extra TEXT,
        timestamp TEXT
    )
    """)

    con.commit()
    con.close()


def save_log(category, data):

    con = connect()
    cur = con.cursor()

    cur.execute(
        """
        INSERT INTO logs
        (category, type, user_id, moderator_id, channel_id, message, extra, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            category,
            data.get("type"),
            data.get("user"),
            data.get("by"),
            data.get("channel"),
            data.get("message"),
            str(data),
            str(datetime.utcnow()),
        ),
    )

    con.commit()
    con.close()


setup()
