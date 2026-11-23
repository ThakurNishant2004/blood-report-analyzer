"""Users, sessions, chat messages and daily usage (all stored in SQLite)."""
import hashlib
import hmac
import json
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple

from auth.database import execute, fetch_all, fetch_one
from config.app_config import DAILY_ANALYSIS_LIMIT
from utils.validators import validate_email, validate_password

_ITERATIONS = 120_000


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _hash(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), _ITERATIONS).hex()


# ---------- users ----------
def register_user(name: str, email: str, password: str) -> Tuple[bool, str]:
    if not (name or "").strip():
        return False, "Please enter your name."
    ok, msg = validate_email(email)
    if not ok:
        return False, msg
    ok, msg = validate_password(password)
    if not ok:
        return False, msg
    salt = os.urandom(16).hex()
    try:
        execute(
            "INSERT INTO users (name, email, password_hash, salt, created_at) VALUES (?,?,?,?,?)",
            (name.strip(), email.strip().lower(), _hash(password, salt), salt, _now()),
        )
    except sqlite3.IntegrityError:
        return False, "An account with this email already exists."
    return True, "Account created. You can sign in now."


def authenticate(email: str, password: str) -> Optional[dict]:
    row = fetch_one("SELECT * FROM users WHERE email = ?", ((email or "").strip().lower(),))
    if not row:
        return None
    if hmac.compare_digest(row["password_hash"], _hash(password or "", row["salt"])):
        return {"id": row["id"], "name": row["name"], "email": row["email"]}
    return None


# ---------- chat sessions ----------
def create_session(user_id: int, title: str, report_text: str, patient_info: dict,
                   analysis: str, model_used: str) -> int:
    return execute(
        "INSERT INTO chat_sessions (user_id, title, report_text, patient_info, analysis, model_used, created_at) "
        "VALUES (?,?,?,?,?,?,?)",
        (user_id, title, report_text, json.dumps(patient_info), analysis, model_used, _now()),
    )


def list_sessions(user_id: int) -> List[dict]:
    return fetch_all(
        "SELECT id, title, created_at FROM chat_sessions WHERE user_id = ? ORDER BY id DESC", (user_id,)
    )


def get_session(session_id: int, user_id: int) -> Optional[dict]:
    """Ownership check included: users can only open their own sessions."""
    return fetch_one("SELECT * FROM chat_sessions WHERE id = ? AND user_id = ?", (session_id, user_id))


def delete_session(session_id: int, user_id: int) -> None:
    execute("DELETE FROM chat_sessions WHERE id = ? AND user_id = ?", (session_id, user_id))


def recent_analyses(user_id: int, limit: int = 2) -> List[str]:
    """Short excerpts of the user's latest analyses (used for in-context learning)."""
    rows = fetch_all(
        "SELECT created_at, analysis FROM chat_sessions WHERE user_id = ? AND analysis IS NOT NULL "
        "ORDER BY id DESC LIMIT ?", (user_id, limit))
    return [f"[{r['created_at'][:10]}] {r['analysis'][:700]}" for r in rows]


# ---------- chat messages ----------
def add_message(session_id: int, role: str, content: str) -> None:
    execute("INSERT INTO chat_messages (session_id, role, content, created_at) VALUES (?,?,?,?)",
            (session_id, role, content, _now()))


def get_messages(session_id: int) -> List[dict]:
    return fetch_all("SELECT role, content FROM chat_messages WHERE session_id = ? ORDER BY id", (session_id,))


# ---------- daily limit ----------
def _today_start() -> datetime:
    return datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)


def analyses_today(user_id: int) -> int:
    row = fetch_one("SELECT COUNT(*) AS n FROM usage_log WHERE user_id = ? AND used_at >= ?",
                    (user_id, _today_start().isoformat(timespec="seconds")))
    return row["n"] if row else 0


def remaining_analyses(user_id: int) -> int:
    return max(0, DAILY_ANALYSIS_LIMIT - analyses_today(user_id))


def log_analysis(user_id: int) -> None:
    execute("INSERT INTO usage_log (user_id, used_at) VALUES (?,?)", (user_id, _now()))


def seconds_until_reset() -> int:
    return int((_today_start() + timedelta(days=1) - datetime.now(timezone.utc)).total_seconds())
