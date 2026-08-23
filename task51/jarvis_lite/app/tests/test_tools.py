"""Tests for tools module (calculator, weather, document search)."""

import pytest

from app.tools.calculator import CalculatorTool
from app.tools.weather import WeatherTool
from app.tools.document_search import DocumentSearchTool


class TestCalculatorTool:
    """Test CalculatorTool."""

    def test_simple_addition(self):
        """Test simple addition."""
        tool = CalculatorTool()
        result = tool.execute(expression="2 + 2")
        
        assert result.success
        assert result.result == 4

    def test_complex_expression(self):
        """Test complex mathematical expression."""
        tool = CalculatorTool()
        result = tool.execute(expression="sqrt(16) + 2 * 3")
        
        assert result.success
        assert result.result == 10.0

    def test_trigonometry(self):
        """Test trigonometric functions."""
        tool = CalculatorTool()
        result = tool.execute(expression="sin(0)")
        
        assert result.success
        assert abs(result.result) < 0.001  # sin(0) ≈ 0

    def test_power_operation(self):
        """Test power operation."""
        tool = CalculatorTool()
        result = tool.execute(expression="2 ** 3")
        
        assert result.success
        assert result.result == 8

    def test_caret_to_power_conversion(self):
        """Test that ^ is converted to **."""
        tool = CalculatorTool()
        result = tool.execute(expression="2 ^ 3")
        
        assert result.success
        assert result.result == 8

    def test_division_by_zero(self):
        """Test division by zero error handling."""
        tool = CalculatorTool()
        result = tool.execute(expression="1 / 0")
        
        assert not result.success
        assert "Division by zero" in result.error

    def test_invalid_expression(self):
        """Test invalid expression."""
        tool = CalculatorTool()
        result = tool.execute(expression="2 + + 2")
        
        assert not result.success

    def test_invalid_character(self):
        """Test that invalid characters are rejected."""
        tool = CalculatorTool()
        result = tool.execute(expression="2 + 2; rm -rf /")
        
        assert not result.success
        assert "Invalid character" in result.error

    def test_non_string_expression(self):
        """Test that non-string input is rejected."""
        tool = CalculatorTool()
        result = tool.execute(expression=123)
        
        assert not result.success

    def test_empty_expression(self):
        """Test empty expression."""
        tool = CalculatorTool()
        result = tool.execute(expression="")
        
        assert not result.success

    def test_tool_schema(self):
        """Test tool schema."""
        tool = CalculatorTool()
        schema = tool.get_schema()
        
        assert "properties" in schema
        assert "expression" in schema["properties"]

    def test_tool_metadata(self):
        """Test tool metadata."""
        tool = CalculatorTool()
        
        assert tool.name == "calculator"
        assert "mathematical" in tool.description.lower()


class TestWeatherTool:
    """Test WeatherTool."""

    def test_mock_weather_new_york(self):
        """Test getting mock weather for New York."""
        tool = WeatherTool()
        result = tool.execute(location="New York")
        
        assert result.success
        assert "location" in result.result
        assert result.result["location"] == "New York"
        assert "temperature_f" in result.result

    def test_mock_weather_london(self):
        """Test getting mock weather for London."""
        tool = WeatherTool()
        result = tool.execute(location="London")
        
        assert result.success
        assert result.result["location"] == "London"
        assert result.result["condition"] == "Rainy"

    def test_mock_weather_unknown_location(self):
        """Test weather for unknown location (uses default)."""
        tool = WeatherTool()
        result = tool.execute(location="Unknown City")
        
        assert result.success
        assert "temperature_f" in result.result

    def test_empty_location(self):
        """Test that empty location is rejected."""
        tool = WeatherTool()
        result = tool.execute(location="")
        
        assert not result.success
        assert "empty" in result.error.lower()

    def test_non_string_location(self):
        """Test that non-string location is rejected."""
        tool = WeatherTool()
        result = tool.execute(location=123)
        
        assert not result.success

    def test_tool_schema(self):
        """Test weather tool schema."""
        tool = WeatherTool()
        schema = tool.get_schema()
        
        assert "properties" in schema
        assert "location" in schema["properties"]

    def test_tool_metadata(self):
        """Test tool metadata."""
        tool = WeatherTool()
        
        assert tool.name == "weather"
        assert "weather" in tool.description.lower()

    def test_weather_has_all_fields(self):
        """Test that weather result has all expected fields."""
        tool = WeatherTool()
        result = tool.execute(location="Paris")
        
        assert result.success
        data = result.result
        required_fields = [
            "location",
            "temperature_f",
            "feels_like_f",
            "humidity_percent",
            "condition",
            "wind_speed_mph"
        ]
        for field in required_fields:
            assert field in data


class TestDocumentSearchTool:
    """Test DocumentSearchTool."""

    def test_tool_creation(self):
        """Test tool can be created."""
        tool = DocumentSearchTool()
        
        assert tool.name == "search_documents"
        assert "search" in tool.description.lower()

    def test_tool_schema(self):
        """Test document search tool schema."""
        tool = DocumentSearchTool()
        schema = tool.get_schema()
        
        assert "properties" in schema
        assert "query" in schema["properties"]

    def test_no_rag_service(self):
        """Test that tool fails gracefully without RAG service."""
        tool = DocumentSearchTool()
        result = tool.execute(query="test query")
        
        assert not result.success
        assert "RAG service" in result.error

    def test_empty_query(self):
        """Test that empty query is rejected."""
        tool = DocumentSearchTool()
        result = tool.execute(query="")
        
        assert not result.success
        assert "empty" in result.error.lower()

    def test_non_string_query(self):
        """Test that non-string query is rejected."""
        tool = DocumentSearchTool()
        result = tool.execute(query=123)
        
        assert not result.success

    def test_tool_metadata(self):
        """Test tool metadata."""
        tool = DocumentSearchTool()
        
        assert tool.name == "search_documents"
        assert "document" in tool.description.lower()
