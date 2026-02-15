import sqlite3
import os
from datetime import datetime

DB_PATH = "data/logs/logs.db"

os.makedirs("data/logs", exist_ok=True)


def connect():
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

    cur.execute("""
        INSERT INTO logs
        (category, type, user_id, moderator_id, channel_id, message, extra, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (

        category,
        data.get("type"),
        data.get("user"),
        data.get("by"),
        data.get("channel"),
        data.get("message"),
        str(data),
        str(datetime.utcnow())

    ))

    con.commit()
    con.close()


setup()
