"""
plugins/weather_plugin.py
----------------------------
Sample plugin: current weather via Open-Meteo (free, no API key).
"""

import requests

from core.base_plugin import BasePlugin, PluginExecutionError

_WEATHER_CODES = {
    0: "clear sky", 1: "mainly clear", 2: "partly cloudy", 3: "overcast",
    45: "fog", 51: "light drizzle", 61: "slight rain", 63: "moderate rain",
    65: "heavy rain", 71: "slight snow", 80: "rain showers", 95: "thunderstorm",
}


class WeatherPlugin(BasePlugin):
    name = "weather"
    description = "Get the current weather for a city."
    input_schema = {
        "type": "object",
        "properties": {
            "city": {"type": "string", "description": "City name, e.g. 'Islamabad'."},
        },
        "required": ["city"],
    }

    def execute(self, city: str) -> str:
        try:
            geo = requests.get(
                "https://geocoding-api.open-meteo.com/v1/search",
                params={"name": city, "count": 1}, timeout=10,
            )
            geo.raise_for_status()
            results = geo.json().get("results")
        except requests.RequestException as exc:
            raise PluginExecutionError(f"Could not reach the geocoding service: {exc}")

        if not results:
            raise PluginExecutionError(f"Could not find a location matching '{city}'.")

        match = results[0]
        try:
            forecast = requests.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": match["latitude"], "longitude": match["longitude"],
                    "current": "temperature_2m,relative_humidity_2m,weather_code",
                    "timezone": "auto",
                },
                timeout=10,
            )
            forecast.raise_for_status()
            current = forecast.json().get("current", {})
        except requests.RequestException as exc:
            raise PluginExecutionError(f"Could not reach the weather service: {exc}")

        if not current:
            raise PluginExecutionError(f"No current weather data available for '{city}'.")

        condition = _WEATHER_CODES.get(current.get("weather_code"), "unknown conditions")
        return (
            f"{match.get('name', city)}: {condition}, {current.get('temperature_2m')}\u00b0C, "
            f"humidity {current.get('relative_humidity_2m')}%"
        )
