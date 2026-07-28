"""
tools/weather_tool.py
-----------------------
Weather information for any location, using Open-Meteo -- a free
weather API that requires NO API key. Two-step lookup:
  1. Geocode the place name to latitude/longitude.
  2. Fetch the current weather forecast for those coordinates.
"""

import requests
from langchain_core.tools import tool

from config import OPEN_METEO_GEOCODE_URL, OPEN_METEO_FORECAST_URL
from utils import get_logger

logger = get_logger(__name__)

# WMO weather interpretation codes -> human-readable description
_WEATHER_CODES = {
    0: "clear sky", 1: "mainly clear", 2: "partly cloudy", 3: "overcast",
    45: "fog", 48: "depositing rime fog",
    51: "light drizzle", 53: "moderate drizzle", 55: "dense drizzle",
    61: "slight rain", 63: "moderate rain", 65: "heavy rain",
    71: "slight snow", 73: "moderate snow", 75: "heavy snow",
    77: "snow grains",
    80: "slight rain showers", 81: "moderate rain showers", 82: "violent rain showers",
    85: "slight snow showers", 86: "heavy snow showers",
    95: "thunderstorm", 96: "thunderstorm with slight hail", 99: "thunderstorm with heavy hail",
}


class WeatherError(Exception):
    """Raised when location lookup or forecast retrieval fails."""


def _geocode(location: str):
    resp = requests.get(
        OPEN_METEO_GEOCODE_URL, params={"name": location, "count": 1}, timeout=10
    )
    resp.raise_for_status()
    data = resp.json()
    results = data.get("results")
    if not results:
        raise WeatherError(f"Could not find a location matching '{location}'.")
    match = results[0]
    return match["latitude"], match["longitude"], match.get("name", location), match.get("country", "")


def _fetch_forecast(lat: float, lon: float):
    resp = requests.get(
        OPEN_METEO_FORECAST_URL,
        params={
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code",
            "timezone": "auto",
        },
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json().get("current", {})


def get_weather(location: str) -> str:
    lat, lon, resolved_name, country = _geocode(location)
    current = _fetch_forecast(lat, lon)

    if not current:
        raise WeatherError(f"No current weather data available for '{location}'.")

    temp = current.get("temperature_2m")
    humidity = current.get("relative_humidity_2m")
    wind = current.get("wind_speed_10m")
    code = current.get("weather_code")
    description = _WEATHER_CODES.get(code, "unknown conditions")

    place_label = f"{resolved_name}, {country}" if country else resolved_name
    return (
        f"Weather in {place_label}: {description}, {temp}\u00b0C, "
        f"humidity {humidity}%, wind {wind} km/h."
    )


@tool
def weather(location: str) -> str:
    """
    Get the current weather for a city or place name, e.g. "Islamabad"
    or "New York". Returns temperature, conditions, humidity, and wind speed.
    """
    logger.info("Weather tool invoked for location: %r", location)
    try:
        return get_weather(location)
    except WeatherError as exc:
        logger.warning("Weather error: %s", exc)
        return f"Error: {exc}"
    except requests.RequestException as exc:
        logger.error("Weather API request failed: %s", exc)
        return f"Error: could not reach the weather service ({exc})"
