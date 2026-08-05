"""
Date / Time tool — Phase 12.

Provides the current UTC date and time, date arithmetic (add/subtract
days, weeks, months), and day-of-week lookups.  All operations are
deterministic and require no external API.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

import re


def get_current_datetime(timezone_name: str = "UTC") -> str:
    """
    Return the current date and time.

    Args:
        timezone_name: Timezone label to display.  Only "UTC" is supported
                       for true offset resolution; any other string is shown
                       as a label only.

    Returns:
        A formatted date-time string, e.g.
        "Monday, 03 August 2026 — 16:42:07 UTC"
    """
    now = datetime.now(tz=timezone.utc)
    day_name = now.strftime("%A")
    formatted = now.strftime(f"%A, %d %B %Y — %H:%M:%S {timezone_name}")
    return formatted


def add_days(date_str: str, days: int) -> str:
    """
    Add (or subtract if negative) a number of days to a date.

    Args:
        date_str: ISO-format date string, e.g. "2026-08-03"
        days: Integer number of days to add (negative to subtract)

    Returns:
        The resulting date as an ISO string, e.g. "2026-09-15"
    """
    try:
        d = datetime.fromisoformat(date_str.strip())
        result = d + timedelta(days=days)
        return result.strftime("%Y-%m-%d (%A)")
    except ValueError as exc:
        return f"Error parsing date '{date_str}': {exc}"


def days_between(date_a: str, date_b: str) -> str:
    """
    Calculate the number of days between two ISO dates.

    Args:
        date_a: Start date, ISO format e.g. "2026-01-01"
        date_b: End date, ISO format e.g. "2026-12-31"

    Returns:
        A string like "364 days (date_b is after date_a)"
    """
    try:
        a = datetime.fromisoformat(date_a.strip())
        b = datetime.fromisoformat(date_b.strip())
        delta = (b - a).days
        direction = "after" if delta >= 0 else "before"
        return f"{abs(delta)} days ({date_b} is {direction} {date_a})"
    except ValueError as exc:
        return f"Error: {exc}"


def day_of_week(date_str: str) -> str:
    """
    Return the day of the week for a given ISO date.

    Args:
        date_str: ISO date string, e.g. "2026-08-03"

    Returns:
        A string like "2026-08-03 is a Monday"
    """
    try:
        d = datetime.fromisoformat(date_str.strip())
        return f"{date_str} is a {d.strftime('%A')}"
    except ValueError as exc:
        return f"Error: {exc}"
