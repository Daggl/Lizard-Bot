import sqlite3
import os
import json

DB = "data/logs/logs.db"


def connect():
    os.makedirs("data/logs", exist_ok=True)
    return sqlite3.connect(DB)


def setup():

    conn = connect()
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS chat_logs(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        data TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS member_logs(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        data TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS mod_logs(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        data TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS voice_logs(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        data TEXT
    )
    """)

    conn.commit()
    conn.close()


def save_chat(data):

    conn = connect()
    conn.execute(
        "INSERT INTO chat_logs(data) VALUES(?)",
        (json.dumps(data),)
    )
    conn.commit()
    conn.close()


def save_member(data):

    conn = connect()
    conn.execute(
        "INSERT INTO member_logs(data) VALUES(?)",
        (json.dumps(data),)
    )
    conn.commit()
    conn.close()


def save_mod(data):

    conn = connect()
    conn.execute(
        "INSERT INTO mod_logs(data) VALUES(?)",
        (json.dumps(data),)
    )
    conn.commit()
    conn.close()


def save_voice(data):

    conn = connect()
    conn.execute(
        "INSERT INTO voice_logs(data) VALUES(?)",
        (json.dumps(data),)
    )
    conn.commit()
    conn.close()
