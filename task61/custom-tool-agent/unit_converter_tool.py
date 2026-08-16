"""
unit_converter_tool.py
------------------------
A custom LangChain tool: converts a numeric value between units of
length, weight, or temperature. Fully self-contained (no external API),
which makes it easy to test deterministically.

Supported units:
  Length      : km, m, cm, miles, feet, inches
  Weight      : kg, g, lbs, oz
  Temperature : celsius, fahrenheit, kelvin
"""

from langchain_core.tools import tool

# Linear categories: factor to convert 1 unit -> the category's base unit
_LENGTH_TO_METERS = {
    "km": 1000.0, "m": 1.0, "cm": 0.01,
    "miles": 1609.34, "feet": 0.3048, "inches": 0.0254,
}
_WEIGHT_TO_GRAMS = {
    "kg": 1000.0, "g": 1.0, "lbs": 453.592, "oz": 28.3495,
}

_TEMPERATURE_UNITS = {"celsius", "fahrenheit", "kelvin"}


class UnitConverterError(Exception):
    """Raised for unsupported units or mismatched categories."""


def _convert_temperature(value: float, from_unit: str, to_unit: str) -> float:
    # Normalize to Celsius first, then to the target unit
    if from_unit == "celsius":
        celsius = value
    elif from_unit == "fahrenheit":
        celsius = (value - 32) * 5 / 9
    elif from_unit == "kelvin":
        celsius = value - 273.15
    else:
        raise UnitConverterError(f"Unsupported temperature unit: {from_unit}")

    if to_unit == "celsius":
        return celsius
    elif to_unit == "fahrenheit":
        return celsius * 9 / 5 + 32
    elif to_unit == "kelvin":
        return celsius + 273.15
    else:
        raise UnitConverterError(f"Unsupported temperature unit: {to_unit}")


def _convert_linear(value: float, from_unit: str, to_unit: str, table: dict, category: str) -> float:
    if from_unit not in table or to_unit not in table:
        raise UnitConverterError(
            f"Unsupported {category} unit(s): '{from_unit}' / '{to_unit}'. "
            f"Supported: {sorted(table)}"
        )
    base_value = value * table[from_unit]
    return base_value / table[to_unit]


def convert(value: float, from_unit: str, to_unit: str) -> float:
    """Core conversion logic, usable directly in Python (and by the tool below)."""
    from_unit = from_unit.strip().lower()
    to_unit = to_unit.strip().lower()

    if from_unit in _TEMPERATURE_UNITS or to_unit in _TEMPERATURE_UNITS:
        return _convert_temperature(value, from_unit, to_unit)
    if from_unit in _LENGTH_TO_METERS and to_unit in _LENGTH_TO_METERS:
        return _convert_linear(value, from_unit, to_unit, _LENGTH_TO_METERS, "length")
    if from_unit in _WEIGHT_TO_GRAMS and to_unit in _WEIGHT_TO_GRAMS:
        return _convert_linear(value, from_unit, to_unit, _WEIGHT_TO_GRAMS, "weight")

    raise UnitConverterError(
        f"Cannot convert between '{from_unit}' and '{to_unit}' -- unrecognized or "
        "mismatched unit categories. Supported: length (km, m, cm, miles, feet, "
        "inches), weight (kg, g, lbs, oz), temperature (celsius, fahrenheit, kelvin)."
    )


@tool
def unit_converter(value: float, from_unit: str, to_unit: str) -> str:
    """
    Convert a numeric value from one unit to another. Supports:
    - Length: km, m, cm, miles, feet, inches
    - Weight: kg, g, lbs, oz
    - Temperature: celsius, fahrenheit, kelvin
    Use this whenever the user asks to convert a measurement, distance,
    weight, or temperature between units (e.g. "10 km to miles",
    "98.6 fahrenheit to celsius", "5 kg in lbs").
    """
    try:
        result = convert(value, from_unit, to_unit)
    except UnitConverterError as exc:
        return f"Error: {exc}"
    return f"{value} {from_unit} = {round(result, 4)} {to_unit}"
