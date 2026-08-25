"""
plugins/unit_converter_plugin.py
------------------------------------
Sample plugin: unit conversion for length, weight, and temperature.
"""

from core.base_plugin import BasePlugin, PluginExecutionError

_LENGTH_TO_METERS = {"km": 1000.0, "m": 1.0, "cm": 0.01, "miles": 1609.34, "feet": 0.3048, "inches": 0.0254}
_WEIGHT_TO_GRAMS = {"kg": 1000.0, "g": 1.0, "lbs": 453.592, "oz": 28.3495}
_TEMPERATURE_UNITS = {"celsius", "fahrenheit", "kelvin"}


def _convert_temperature(value, from_unit, to_unit):
    if from_unit == "celsius":
        celsius = value
    elif from_unit == "fahrenheit":
        celsius = (value - 32) * 5 / 9
    elif from_unit == "kelvin":
        celsius = value - 273.15
    else:
        raise PluginExecutionError(f"Unsupported temperature unit: {from_unit}")

    if to_unit == "celsius":
        return celsius
    elif to_unit == "fahrenheit":
        return celsius * 9 / 5 + 32
    elif to_unit == "kelvin":
        return celsius + 273.15
    raise PluginExecutionError(f"Unsupported temperature unit: {to_unit}")


class UnitConverterPlugin(BasePlugin):
    name = "unit_converter"
    description = "Convert a value between units of length, weight, or temperature."
    input_schema = {
        "type": "object",
        "properties": {
            "value": {"type": "number", "description": "The numeric value to convert."},
            "from_unit": {"type": "string", "description": "Source unit, e.g. 'km', 'kg', 'celsius'."},
            "to_unit": {"type": "string", "description": "Target unit, e.g. 'miles', 'lbs', 'fahrenheit'."},
        },
        "required": ["value", "from_unit", "to_unit"],
    }

    def execute(self, value: float, from_unit: str, to_unit: str) -> str:
        from_unit = from_unit.strip().lower()
        to_unit = to_unit.strip().lower()

        if from_unit in _TEMPERATURE_UNITS or to_unit in _TEMPERATURE_UNITS:
            result = _convert_temperature(value, from_unit, to_unit)
        elif from_unit in _LENGTH_TO_METERS and to_unit in _LENGTH_TO_METERS:
            result = value * _LENGTH_TO_METERS[from_unit] / _LENGTH_TO_METERS[to_unit]
        elif from_unit in _WEIGHT_TO_GRAMS and to_unit in _WEIGHT_TO_GRAMS:
            result = value * _WEIGHT_TO_GRAMS[from_unit] / _WEIGHT_TO_GRAMS[to_unit]
        else:
            raise PluginExecutionError(
                f"Cannot convert between '{from_unit}' and '{to_unit}' -- unrecognized or mismatched units."
            )

        return f"{value} {from_unit} = {round(result, 4)} {to_unit}"
