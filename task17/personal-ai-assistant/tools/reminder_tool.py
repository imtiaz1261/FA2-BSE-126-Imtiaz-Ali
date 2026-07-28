"""
tools/reminder_tool.py
------------------------
Reminder management tool, backed by SQLite (db.py).

Natural language times (e.g. "tomorrow at 9 AM") are parsed with the
`dateparser` library into an absolute ISO datetime before storage.

Scope note: this stores and lists reminders; it does not run a
background scheduler to push notifications at the target time (see
README "Future improvements" for how to extend this with APScheduler
or a system notification library).
"""

from langchain_core.tools import tool

import db
from utils import get_logger

logger = get_logger(__name__)


class ReminderParseError(Exception):
    """Raised when the reminder time can't be understood."""


def parse_datetime(when: str) -> str:
    import dateparser

    parsed = dateparser.parse(
        when, settings={"PREFER_DATES_FROM": "future"}
    )
    if parsed is None:
        raise ReminderParseError(
            f"Could not understand the time '{when}'. Try something like "
            "'tomorrow at 9 AM' or '2026-07-25 14:00'."
        )
    return parsed.isoformat(timespec="minutes")


@tool
def create_reminder(text: str, when: str) -> str:
    """
    Create a reminder. Use this when the user says things like "remind
    me to X" or "create a reminder for tomorrow at 9 AM".

    Args:
        text: what the reminder is about, e.g. "team meeting".
        when: the natural-language time, e.g. "tomorrow at 9 AM",
            "next Monday", or an ISO datetime.
    """
    logger.info("Creating reminder: text=%r when=%r", text, when)
    try:
        remind_at = parse_datetime(when)
    except ReminderParseError as exc:
        return f"Error: {exc}"

    reminder_id = db.add_reminder(text, remind_at)
    return f"Reminder #{reminder_id} set: \"{text}\" at {remind_at}."


@tool
def list_reminders() -> str:
    """List all upcoming reminders, soonest first."""
    rows = db.list_reminders()
    if not rows:
        return "You have no reminders set."
    lines = [f"#{row['id']} {row['remind_at']}: {row['text']}" for row in rows]
    return "\n".join(lines)


@tool
def delete_reminder(reminder_id: int) -> str:
    """Delete a reminder by its numeric ID (use list_reminders first to find the ID)."""
    deleted = db.delete_reminder(int(reminder_id))
    if deleted:
        return f"Reminder #{reminder_id} deleted."
    return f"No reminder found with ID #{reminder_id}."
