"""Conversion maths and unit normalisation. No LLM is used in this module."""

from __future__ import annotations


class ConversionError(ValueError):
    """Raised when a unit or a conversion is not supported."""


UNITS = {
    # canonical: (category, factor to category base; temperature uses formulas below)
    "kilometer": ("length", 1000.0), "mile": ("length", 1609.344),
    "meter": ("length", 1.0), "foot": ("length", 0.3048),
    "centimeter": ("length", 0.01), "inch": ("length", 0.0254),
    "kilogram": ("weight", 1000.0), "pound": ("weight", 453.59237),
    "gram": ("weight", 1.0), "ounce": ("weight", 28.349523125),
    "liter": ("volume", 1.0), "gallon": ("volume", 3.785411784),
    "milliliter": ("volume", 0.001),
    "celsius": ("temperature", None), "fahrenheit": ("temperature", None),
    "kelvin": ("temperature", None),
}

ALIASES = {
    "km": "kilometer", "kilometer": "kilometer", "kilometers": "kilometer", "kms": "kilometer",
    "mi": "mile", "mile": "mile", "miles": "mile",
    "m": "meter", "meter": "meter", "meters": "meter", "metre": "meter", "metres": "meter",
    "ft": "foot", "foot": "foot", "feet": "foot",
    "cm": "centimeter", "centimeter": "centimeter", "centimeters": "centimeter",
    "in": "inch", "inch": "inch", "inches": "inch",
    "kg": "kilogram", "kilogram": "kilogram", "kilograms": "kilogram", "kgs": "kilogram",
    "g": "gram", "gram": "gram", "grams": "gram", "gm": "gram", "gms": "gram",
    "lb": "pound", "lbs": "pound", "pound": "pound", "pounds": "pound",
    "oz": "ounce", "ounce": "ounce", "ounces": "ounce",
    "l": "liter", "liter": "liter", "liters": "liter", "litre": "liter", "litres": "liter",
    "ml": "milliliter", "milliliter": "milliliter", "milliliters": "milliliter",
    "gal": "gallon", "gallon": "gallon", "gallons": "gallon",
    "c": "celsius", "°c": "celsius", "celsius": "celsius", "centigrade": "celsius",
    "f": "fahrenheit", "°f": "fahrenheit", "fahrenheit": "fahrenheit",
    "k": "kelvin", "kelvin": "kelvin", "kelvins": "kelvin",
}


def normalize_unit(unit: str) -> str:
    if not isinstance(unit, str):
        raise ConversionError("A unit must be text.")
    key = unit.strip().lower().replace("degrees ", "").replace("degree ", "")
    if key not in ALIASES:
        raise ConversionError(f"Unsupported unit: '{unit}'.")
    return ALIASES[key]


def get_unit_label(unit: str, value: float | None = None) -> str:
    """Return a readable singular/plural name for a unit."""
    canonical = normalize_unit(unit)
    if canonical == "foot" and value is not None and abs(value) != 1:
        return "feet"
    return canonical if value is not None and abs(value) == 1 else canonical + "s"


def _temperature_to_celsius(value: float, unit: str) -> float:
    if unit == "celsius": return value
    if unit == "fahrenheit": return (value - 32) * 5 / 9
    return value - 273.15


def _celsius_to_temperature(value: float, unit: str) -> float:
    if unit == "celsius": return value
    if unit == "fahrenheit": return value * 9 / 5 + 32
    return value + 273.15


def convert_unit(value: float, from_unit: str, to_unit: str) -> float:
    """Convert a numeric value between supported compatible units."""
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ConversionError("Value must be a valid number.") from exc
    source, target = normalize_unit(from_unit), normalize_unit(to_unit)
    source_category, source_factor = UNITS[source]
    target_category, target_factor = UNITS[target]
    if source_category != target_category:
        raise ConversionError(f"Cannot convert {source} to {target}: they are different categories.")
    if source_category == "temperature":
        return _celsius_to_temperature(_temperature_to_celsius(number, source), target)
    return number * source_factor / target_factor
