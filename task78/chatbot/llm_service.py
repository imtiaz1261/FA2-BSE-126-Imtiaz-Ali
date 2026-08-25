"""Groq tool-calling parser, with a local parser fallback when no key is configured."""

from __future__ import annotations
import json, os
from dotenv import load_dotenv
from .parser import ConversionRequest, ParseError, parse_locally, validate_request

load_dotenv()

TOOL = {"type": "function", "function": {"name": "extract_conversion", "description": "Extract one requested unit conversion. Never calculate it.", "parameters": {"type": "object", "properties": {"value": {"type": "number"}, "from_unit": {"type": "string"}, "to_unit": {"type": "string"}}, "required": ["value", "from_unit", "to_unit"], "additionalProperties": False}}}

SYSTEM = "Extract the numeric value, source unit, and target unit from English or Urdu/Hinglish conversion requests. Call the tool only when all three are explicit. Do not calculate."


def extract_conversion(text: str) -> tuple[ConversionRequest, str]:
    """Return parsed request and parser source (Groq or local fallback)."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return parse_locally(text), "local parser"
    try:
        from groq import Groq
        completion = Groq(api_key=api_key).chat.completions.create(
            model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
            messages=[{"role": "system", "content": SYSTEM}, {"role": "user", "content": text}],
            tools=[TOOL], tool_choice={"type": "function", "function": {"name": "extract_conversion"}},
            temperature=0,
        )
        calls = completion.choices[0].message.tool_calls or []
        if not calls: raise ParseError("I need a value and two units. Example: '5 km to miles'.")
        return validate_request(json.loads(calls[0].function.arguments)), "Groq"
    except ParseError: raise
    except Exception as exc:
        raise ParseError(f"I couldn't process that request right now ({type(exc).__name__}). Please try again.") from exc
