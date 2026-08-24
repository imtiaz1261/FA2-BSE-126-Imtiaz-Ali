"""Weather tool — fetches current weather via wttr.in (no API key needed)."""
from __future__ import annotations
from backend.core.logging import get_logger

logger = get_logger(__name__)


def get_weather(location: str) -> str:
    """
    Get current weather for a location.
    Uses wttr.in which requires no API key.
    """
    try:
        import httpx
        url = f"https://wttr.in/{location}?format=4"
        with httpx.Client(timeout=10) as client:
            response = client.get(url, headers={"User-Agent": "AIHub/1.0"})
        if response.status_code == 200:
            weather = response.text.strip()
            logger.info("weather_tool_used", location=location)
            return f"Current weather for {location}:\n{weather}"
        return f"Could not retrieve weather for '{location}' (HTTP {response.status_code})"
    except ImportError:
        return "Weather tool requires httpx: pip install httpx"
    except Exception as exc:
        logger.error("weather_tool_failed", error=str(exc))
        return f"Weather lookup failed: {exc}"
