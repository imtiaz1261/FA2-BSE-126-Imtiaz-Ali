"""Date/time tool — returns current date, time, and timezone info."""
from __future__ import annotations
from datetime import datetime, timezone
from backend.core.logging import get_logger

logger = get_logger(__name__)


def get_datetime(timezone_name: str = "UTC") -> str:
    """
    Return the current date and time.
    timezone_name: e.g. 'UTC', 'US/Eastern', 'Europe/London'
    """
    try:
        import pytz
        tz = pytz.timezone(timezone_name)
        now = datetime.now(tz)
        logger.info("datetime_tool_used", tz=timezone_name)
        return (
            f"Current date and time:\n"
            f"  Date:     {now.strftime('%A, %B %d, %Y')}\n"
            f"  Time:     {now.strftime('%H:%M:%S')}\n"
            f"  Timezone: {timezone_name}\n"
            f"  UTC:      {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
            f"  ISO 8601: {now.isoformat()}"
        )
    except Exception as exc:
        now = datetime.now(timezone.utc)
        return (
            f"Current date and time (UTC):\n"
            f"  Date:     {now.strftime('%A, %B %d, %Y')}\n"
            f"  Time:     {now.strftime('%H:%M:%S UTC')}\n"
            f"  ISO 8601: {now.isoformat()}"
        )
