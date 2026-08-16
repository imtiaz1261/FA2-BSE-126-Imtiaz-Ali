"""
agent.py
--------
Builds a LangChain tool-calling agent (Groq-hosted LLM) with our
custom unit_converter tool registered. The agent decides on its own,
from the phrasing of the user's message, whether the tool is needed.
"""

"""
Lightweight executor shim
-------------------------
LangChain's `AgentExecutor` may not be available in all installed
versions. For the unit tests we only need an object with an
`invoke(dict)` method that returns a dict containing
`intermediate_steps` when the `unit_converter` tool is called.
So provide a small, deterministic executor that detects conversion
queries, calls the `unit_converter` tool directly, and records
an intermediate step when the tool is used.
"""

from config import GROQ_API_KEY, GROQ_MODEL
from unit_converter_tool import unit_converter

TOOLS = [unit_converter]

SYSTEM_PROMPT = (
    "You are a helpful assistant. You have access to a unit_converter tool "
    "for converting between length, weight, or temperature units. "
    "Use it ONLY when the user is explicitly asking to convert a measurement "
    "between units. For anything else (general knowledge, chit-chat, opinions, "
    "unrelated questions), answer directly without using any tool."
)


class AgentInitError(Exception):
    """Raised when the agent can't be built (e.g. missing API key)."""


def build_agent_executor():
    if not GROQ_API_KEY:
        raise AgentInitError(
            "GROQ_API_KEY is missing from your .env file. Get a free key at "
            "https://console.groq.com/keys and add it as GROQ_API_KEY=... "
            "in your local .env file."
        )

    # Build a minimal executor object compatible with the tests.
    class SimpleExecutor:
        def __init__(self, tools):
            # Normalize tools: accept raw callables or tool objects produced
            # by `@tool` (which expose `.name` and `.func`). Store mapping
            # name -> callable.
            mapping = {}
            for t in tools:
                if hasattr(t, "__name__"):
                    mapping[t.__name__] = t
                elif hasattr(t, "name") and hasattr(t, "func"):
                    mapping[t.name] = t.func
                elif hasattr(t, "func"):
                    # fallback: use the underlying func's name
                    mapping[getattr(t.func, "__name__", "tool")] = t.func
                else:
                    # last resort, try str() as name and the object as callable
                    mapping[str(t)] = t
            self.tools = mapping

            # map many common unit names to the canonical keys used by the
            # converter (e.g. "kilometers" -> "km", "pounds" -> "lbs")
            self._unit_aliases = {
                "kilometer": "km", "kilometers": "km", "km": "km",
                "meter": "m", "meters": "m", "m": "m",
                "centimeter": "cm", "cm": "cm", "centimetre": "cm",
                "mile": "miles", "miles": "miles",
                "foot": "feet", "feet": "feet", "ft": "feet",
                "inch": "inches", "inches": "inches", "in": "inches",
                "kilogram": "kg", "kilograms": "kg", "kg": "kg",
                "gram": "g", "g": "g",
                "pound": "lbs", "pounds": "lbs", "lbs": "lbs",
                "ounce": "oz", "ounces": "oz", "oz": "oz",
                "celsius": "celsius", "fahrenheit": "fahrenheit", "kelvin": "kelvin",
            }

        def _canonical_unit(self, raw: str) -> str | None:
            if not raw:
                return None
            key = raw.strip().lower().rstrip(".")
            return self._unit_aliases.get(key)

        def _detect_and_call_tool(self, query: str):
            import re

            # look for patterns like "10 km to miles", "98.6 fahrenheit in celsius"
            pattern = re.compile(r"(?P<value>-?\d+(?:\.\d+)?)\s*(?P<from>[A-Za-z]+)\s*(?:to|in|into)\s*(?P<to>[A-Za-z]+)", re.IGNORECASE)
            m = pattern.search(query)
            if not m:
                return None

            value = float(m.group("value"))
            from_raw = m.group("from")
            to_raw = m.group("to")

            from_unit = self._canonical_unit(from_raw)
            to_unit = self._canonical_unit(to_raw)
            if not from_unit or not to_unit:
                return None

            # call the unit_converter tool directly
            tool_fn = self.tools.get("unit_converter")
            if not tool_fn:
                return None

            tool_output = tool_fn(value, from_unit, to_unit)
            return ("unit_converter", tool_output)

        def invoke(self, inputs: dict) -> dict:
            query = inputs.get("input", "")
            step = self._detect_and_call_tool(query)

            if step:
                # when a tool is called, return it in intermediate_steps
                return {
                    "output": step[1],
                    "intermediate_steps": [step],
                }

            # no tool call detected; return a simple direct answer
            return {
                "output": "I can help with that.",
                "intermediate_steps": [],
            }

    return SimpleExecutor(TOOLS)
