"""
tools/notes_tool.py
---------------------
Note-taking tool, backed by SQLite (db.py).
"""

from langchain_core.tools import tool

import db
from utils import get_logger

logger = get_logger(__name__)


@tool
def save_note(content: str) -> str:
    """
    Save a note for the user. Use this when the user says things like
    "save this note", "remember that...", or "take a note: ...".
    """
    logger.info("Saving note: %r", content)
    note_id = db.add_note(content)
    return f"Note #{note_id} saved: \"{content}\""


@tool
def list_notes() -> str:
    """List all previously saved notes, most recent first."""
    rows = db.list_notes()
    if not rows:
        return "You have no saved notes yet."
    lines = [f"#{row['id']} ({row['created_at']}): {row['content']}" for row in rows]
    return "\n".join(lines)


@tool
def delete_note(note_id: int) -> str:
    """Delete a saved note by its numeric ID (use list_notes first to find the ID)."""
    deleted = db.delete_note(int(note_id))
    if deleted:
        return f"Note #{note_id} deleted."
    return f"No note found with ID #{note_id}."
