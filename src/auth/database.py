"""SQLite helpers and schema (users, chat_sessions, chat_messages, usage_log)."""
import contextlib
import os
import sqlite3

from config.app_config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    salt TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS chat_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    report_text TEXT NOT NULL,
    patient_info TEXT,
    analysis TEXT,
    model_used TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS chat_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS usage_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    used_at TEXT NOT NULL
);
"""


def _connect() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    with contextlib.closing(_connect()) as conn:
        conn.executescript(SCHEMA)
        conn.commit()


def fetch_all(sql: str, params: tuple = ()) -> list:
    with contextlib.closing(_connect()) as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def fetch_one(sql: str, params: tuple = ()):
    rows = fetch_all(sql, params)
    return rows[0] if rows else None


def execute(sql: str, params: tuple = ()) -> int:
    with contextlib.closing(_connect()) as conn:
        cur = conn.execute(sql, params)
        conn.commit()
        return cur.lastrowid
