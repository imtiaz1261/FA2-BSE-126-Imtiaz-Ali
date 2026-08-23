"""
Weather Tool — fetches weather information for a location.

Uses OpenWeatherMap API (with fallback mock data for demo).
"""

import logging
from typing import Any, Dict, Optional

from app.config.settings import settings
from app.core.exceptions import ToolError
from app.tools.base import BaseTool, ToolOutput

logger = logging.getLogger(__name__)


class WeatherTool(BaseTool):
    """Tool for fetching weather information."""

    def __init__(self) -> None:
        super().__init__(
            name="weather",
            description="Fetches current weather information for a location. "
                       "Example: 'weather: New York' or 'get weather for London'"
        )
        self.api_key = settings.OPENWEATHER_API_KEY if hasattr(settings, 'OPENWEATHER_API_KEY') else None
        self.use_mock = not self.api_key  # Use mock data if no API key

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "City name or location to get weather for"
                }
            },
            "required": ["location"]
        }

    def execute(self, location: str, **kwargs) -> ToolOutput:
        """
        Get weather for a location.
        
        Args:
            location: City or location name
            
        Returns:
            ToolOutput with weather data
        """
        try:
            if not isinstance(location, str):
                raise ToolError(f"Location must be a string, got {type(location)}")
            
            if not location.strip():
                raise ToolError("Location cannot be empty")
            
            location = location.strip().title()
            
            if self.use_mock:
                # Return mock weather data for demo
                result = self._get_mock_weather(location)
            else:
                # Use real API
                result = self._get_real_weather(location)
            
            logger.info(f"Weather retrieved for {location}")
            
            return ToolOutput(
                tool_name=self.name,
                success=True,
                result=result,
                metadata={"location": location}
            )
        
        except ToolError as e:
            logger.warning(f"Weather tool error: {e}")
            return ToolOutput(
                tool_name=self.name,
                success=False,
                result=None,
                error=str(e)
            )
        except Exception as e:
            error = f"Weather lookup failed: {e}"
            logger.exception(f"Weather exception: {e}")
            return ToolOutput(
                tool_name=self.name,
                success=False,
                result=None,
                error=error
            )

    def _get_mock_weather(self, location: str) -> Dict[str, Any]:
        """Return mock weather data."""
        mock_data = {
            "New York": {
                "temperature": 72,
                "feels_like": 70,
                "humidity": 65,
                "condition": "Partly Cloudy",
                "wind_speed": 10,
                "uv_index": 5
            },
            "London": {
                "temperature": 59,
                "feels_like": 57,
                "humidity": 72,
                "condition": "Rainy",
                "wind_speed": 12,
                "uv_index": 2
            },
            "Tokyo": {
                "temperature": 78,
                "feels_like": 81,
                "humidity": 70,
                "condition": "Sunny",
                "wind_speed": 5,
                "uv_index": 8
            },
            "Paris": {
                "temperature": 64,
                "feels_like": 62,
                "humidity": 68,
                "condition": "Cloudy",
                "wind_speed": 8,
                "uv_index": 3
            }
        }
        
        # Return mock data or a generic response
        if location in mock_data:
            data = mock_data[location]
        else:
            data = {
                "temperature": 70,
                "feels_like": 68,
                "humidity": 60,
                "condition": "Partly Cloudy",
                "wind_speed": 7,
                "uv_index": 4
            }
        
        return {
            "location": location,
            "temperature_f": data["temperature"],
            "feels_like_f": data["feels_like"],
            "humidity_percent": data["humidity"],
            "condition": data["condition"],
            "wind_speed_mph": data["wind_speed"],
            "uv_index": data["uv_index"],
            "note": "Mock weather data (demo mode)"
        }

    def _get_real_weather(self, location: str) -> Dict[str, Any]:
        """Fetch real weather from API."""
        try:
            import requests
        except ImportError:
            logger.warning("requests library not available, using mock data")
            return self._get_mock_weather(location)
        
        try:
            url = f"https://api.openweathermap.org/data/2.5/weather"
            params = {
                "q": location,
                "appid": self.api_key,
                "units": "imperial"
            }
            
            response = requests.get(url, params=params, timeout=5)
            
            if response.status_code != 200:
                logger.warning(f"Weather API returned status {response.status_code}")
                return self._get_mock_weather(location)
            
            data = response.json()
            
            return {
                "location": data.get("name", location),
                "temperature_f": data["main"]["temp"],
                "feels_like_f": data["main"]["feels_like"],
                "humidity_percent": data["main"]["humidity"],
                "condition": data["weather"][0]["main"],
                "wind_speed_mph": data["wind"]["speed"],
                "pressure_mb": data["main"]["pressure"],
            }
        
        except Exception as e:
            logger.warning(f"Real weather API failed: {e}, using mock data")
            return self._get_mock_weather(location)
