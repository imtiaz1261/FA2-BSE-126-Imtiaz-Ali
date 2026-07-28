"""
db.py
-----
SQLite persistence layer.

Three tables:
  - notes                 : free-form notes the user asks to save
  - reminders              : reminder text + target datetime
  - conversation_log        : full chat history, for cross-session context
                              and simple auditing/debugging

Kept deliberately simple (raw sqlite3, no ORM) so it's easy to read
and extend.
"""

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Iterator, List, Optional, Tuple

from config import DB_PATH
from utils import get_logger

logger = get_logger(__name__)


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    """Create tables if they don't already exist. Safe to call every startup."""
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT NOT NULL,
                remind_at TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS conversation_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
            """
        )
    logger.info("Database initialized at %s", DB_PATH)


# --------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------
def add_note(content: str) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO notes (content, created_at) VALUES (?, ?)",
            (content, datetime.now().isoformat(timespec="seconds")),
        )
        note_id = cur.lastrowid
    logger.info("Note #%d saved.", note_id)
    return note_id


def list_notes() -> List[sqlite3.Row]:
    with get_connection() as conn:
        return conn.execute(
            "SELECT id, content, created_at FROM notes ORDER BY id DESC"
        ).fetchall()


def delete_note(note_id: int) -> bool:
    with get_connection() as conn:
        cur = conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))
        return cur.rowcount > 0


# --------------------------------------------------------------------------
# Reminders
# --------------------------------------------------------------------------
def add_reminder(text: str, remind_at: str) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO reminders (text, remind_at, created_at) VALUES (?, ?, ?)",
            (text, remind_at, datetime.now().isoformat(timespec="seconds")),
        )
        reminder_id = cur.lastrowid
    logger.info("Reminder #%d saved for %s.", reminder_id, remind_at)
    return reminder_id


def list_reminders() -> List[sqlite3.Row]:
    with get_connection() as conn:
        return conn.execute(
            "SELECT id, text, remind_at, created_at FROM reminders ORDER BY remind_at ASC"
        ).fetchall()


def delete_reminder(reminder_id: int) -> bool:
    with get_connection() as conn:
        cur = conn.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))
        return cur.rowcount > 0


# --------------------------------------------------------------------------
# Conversation log
# --------------------------------------------------------------------------
def log_message(session_id: str, role: str, content: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO conversation_log (session_id, role, content, timestamp) "
            "VALUES (?, ?, ?, ?)",
            (session_id, role, content, datetime.now().isoformat(timespec="seconds")),
        )


def get_recent_messages(session_id: str, limit: int = 20) -> List[Tuple[str, str]]:
    """Return the most recent (role, content) pairs for a session, oldest first."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT role, content FROM conversation_log "
            "WHERE session_id = ? ORDER BY id DESC LIMIT ?",
            (session_id, limit),
        ).fetchall()
    return [(row["role"], row["content"]) for row in reversed(rows)]
