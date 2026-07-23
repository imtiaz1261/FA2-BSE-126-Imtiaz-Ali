"""
Tool implementations for the AI Assistant.

- calculate(expression): safely evaluates arithmetic/math expressions.
- get_weather(location, forecast): fetches current weather or a short
  forecast from OpenWeatherMap.

Both functions return a plain dict: {"success": bool, "result"/"error": ...}
so the agent layer can turn failures into friendly messages instead of
crashing.
"""

import ast
import math
import operator
import os

import requests

# ---------------------------------------------------------------------------
# Calculator tool
# ---------------------------------------------------------------------------

# Only these operators/functions are allowed in expressions. This keeps
# eval-like behavior safe -- no arbitrary code execution.
_ALLOWED_BINOPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_ALLOWED_UNARYOPS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}
_ALLOWED_FUNCS = {
    "sqrt": math.sqrt,
    "abs": abs,
    "round": round,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "log": math.log,
    "log10": math.log10,
    "log2": math.log2,
    "exp": math.exp,
    "factorial": math.factorial,
    "floor": math.floor,
    "ceil": math.ceil,
    "pow": pow,
    "degrees": math.degrees,
    "radians": math.radians,
}
_ALLOWED_NAMES = {
    "pi": math.pi,
    "e": math.e,
}


class CalculatorError(Exception):
    pass


def _eval_node(node):
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise CalculatorError(f"Unsupported constant: {node.value!r}")

    if isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in _ALLOWED_BINOPS:
            raise CalculatorError(f"Operator {op_type.__name__} is not allowed")
        left = _eval_node(node.left)
        right = _eval_node(node.right)
        try:
            return _ALLOWED_BINOPS[op_type](left, right)
        except ZeroDivisionError:
            raise CalculatorError("Division by zero")

    if isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in _ALLOWED_UNARYOPS:
            raise CalculatorError(f"Operator {op_type.__name__} is not allowed")
        return _ALLOWED_UNARYOPS[op_type](_eval_node(node.operand))

    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name) or node.func.id not in _ALLOWED_FUNCS:
            raise CalculatorError("Unsupported function call")
        args = [_eval_node(arg) for arg in node.args]
        try:
            return _ALLOWED_FUNCS[node.func.id](*args)
        except ValueError as exc:
            raise CalculatorError(str(exc))

    if isinstance(node, ast.Name):
        if node.id in _ALLOWED_NAMES:
            return _ALLOWED_NAMES[node.id]
        raise CalculatorError(f"Unknown identifier: {node.id}")

    raise CalculatorError(f"Unsupported expression: {ast.dump(node)}")


def calculate(expression: str) -> dict:
    """Safely evaluate a math expression like '245*78' or 'sqrt(625)'."""
    if not expression or not expression.strip():
        return {"success": False, "error": "Empty expression."}
    try:
        tree = ast.parse(expression, mode="eval")
        result = _eval_node(tree.body)
        return {"success": True, "result": result, "expression": expression}
    except CalculatorError as exc:
        return {"success": False, "error": str(exc), "expression": expression}
    except (SyntaxError, ZeroDivisionError, OverflowError, TypeError, ValueError) as exc:
        return {"success": False, "error": f"Invalid expression: {exc}", "expression": expression}


# ---------------------------------------------------------------------------
# Weather tool
# ---------------------------------------------------------------------------

OPENWEATHER_BASE = "https://api.openweathermap.org/data/2.5"


def get_weather(location: str, forecast: bool = False) -> dict:
    """
    Fetch current weather, or a short forecast, for a location.

    forecast=False -> current conditions
    forecast=True  -> next ~24h summary (from the 5 day / 3 hour endpoint)
    """
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key:
        return {"success": False, "error": "OPENWEATHER_API_KEY is not set. Add it to your .env file."}
    if not location or not location.strip():
        return {"success": False, "error": "No location provided."}

    endpoint = "forecast" if forecast else "weather"
    params = {"q": location, "appid": api_key, "units": "metric"}

    try:
        resp = requests.get(f"{OPENWEATHER_BASE}/{endpoint}", params=params, timeout=10)
    except requests.RequestException as exc:
        return {"success": False, "error": f"Network error contacting weather service: {exc}"}

    if resp.status_code == 401:
        return {"success": False, "error": "Weather API key is invalid or not yet activated (new keys can take up to a couple hours)."}
    if resp.status_code == 404:
        return {"success": False, "error": f"Location '{location}' not found."}
    if resp.status_code != 200:
        return {"success": False, "error": f"Weather service returned an error (HTTP {resp.status_code})."}

    data = resp.json()

    if not forecast:
        try:
            return {
                "success": True,
                "location": f"{data['name']}, {data['sys'].get('country', '')}".strip(", "),
                "description": data["weather"][0]["description"],
                "temp_c": data["main"]["temp"],
                "feels_like_c": data["main"]["feels_like"],
                "humidity_pct": data["main"]["humidity"],
                "wind_speed_ms": data["wind"]["speed"],
            }
        except (KeyError, IndexError) as exc:
            return {"success": False, "error": f"Unexpected weather response format: {exc}"}

    # Forecast: summarize the next 8 entries (24h at 3h steps)
    try:
        entries = data["list"][:8]
        rain_chance = max((e.get("pop", 0) for e in entries), default=0) * 100
        temps = [e["main"]["temp"] for e in entries]
        descriptions = {e["weather"][0]["description"] for e in entries}
        return {
            "success": True,
            "location": f"{data['city']['name']}, {data['city'].get('country', '')}".strip(", "),
            "period": "next 24 hours",
            "max_rain_chance_pct": round(rain_chance, 0),
            "temp_range_c": [round(min(temps), 1), round(max(temps), 1)],
            "conditions": sorted(descriptions),
        }
    except (KeyError, IndexError) as exc:
        return {"success": False, "error": f"Unexpected forecast response format: {exc}"}
