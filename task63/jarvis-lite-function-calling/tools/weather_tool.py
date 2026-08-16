"""
tools/weather_tool.py
-----------------------
get_weather(city) -- current weather for a city, via Open-Meteo (free,
no API key: geocode the city name, then fetch current conditions).

Returns structured data (a dict), not a pre-written sentence -- the
LLM composes the final natural-language response from this raw data,
which is the whole point of the function-calling pattern.
"""

import requests

from errors import ToolExecutionError

# --------------------------------------------------------------------------
# Tool schema (OpenAI / Groq function-calling format)
# --------------------------------------------------------------------------
SCHEMA = {
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": (
            "Get the current weather conditions for a specific city. "
            "Use this whenever the user asks about weather, temperature, "
            "or conditions in a location."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "The city name, e.g. 'Islamabad' or 'New York'.",
                },
            },
            "required": ["city"],
        },
    },
}

_WEATHER_CODES = {
    0: "clear sky", 1: "mainly clear", 2: "partly cloudy", 3: "overcast",
    45: "fog", 48: "depositing rime fog",
    51: "light drizzle", 53: "moderate drizzle", 55: "dense drizzle",
    61: "slight rain", 63: "moderate rain", 65: "heavy rain",
    71: "slight snow", 73: "moderate snow", 75: "heavy snow",
    80: "slight rain showers", 81: "moderate rain showers", 82: "violent rain showers",
    95: "thunderstorm",
}


def get_weather(city: str) -> dict:
    """
    Execute the weather lookup. Returns a plain dict of structured data.
    Raises ToolExecutionError on geocoding failure or API/network errors.
    """
    try:
        geo_resp = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": city, "count": 1},
            timeout=10,
        )
        geo_resp.raise_for_status()
        results = geo_resp.json().get("results")
    except requests.RequestException as exc:
        raise ToolExecutionError(f"Could not reach the geocoding service: {exc}") from exc

    if not results:
        raise ToolExecutionError(f"Could not find a location matching '{city}'.")

    match = results[0]
    lat, lon = match["latitude"], match["longitude"]
    resolved_name = match.get("name", city)
    country = match.get("country", "")

    try:
        forecast_resp = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code",
                "timezone": "auto",
            },
            timeout=10,
        )
        forecast_resp.raise_for_status()
        current = forecast_resp.json().get("current", {})
    except requests.RequestException as exc:
        raise ToolExecutionError(f"Could not reach the weather service: {exc}") from exc

    if not current:
        raise ToolExecutionError(f"No current weather data available for '{city}'.")

    return {
        "city": resolved_name,
        "country": country,
        "temperature_c": current.get("temperature_2m"),
        "condition": _WEATHER_CODES.get(current.get("weather_code"), "unknown"),
        "humidity_percent": current.get("relative_humidity_2m"),
        "wind_kph": current.get("wind_speed_10m"),
    }
