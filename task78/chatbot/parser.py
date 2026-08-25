"""Validation and an offline regex parser for common conversion phrasing."""

from __future__ import annotations
import re
from dataclasses import dataclass
from conversion.converter import ALIASES, ConversionError, normalize_unit


class ParseError(ValueError):
    """Raised when a conversion request is incomplete or unclear."""


@dataclass(frozen=True)
class ConversionRequest:
    value: float
    from_unit: str
    to_unit: str


def validate_request(data: dict) -> ConversionRequest:
    if not isinstance(data, dict): raise ParseError("I couldn't understand that request.")
    missing = [name for name in ("value", "from_unit", "to_unit") if data.get(name) in (None, "")]
    if missing:
        raise ParseError("Please include a value, source unit, and target unit. For example: '10 kg to pounds'.")
    try: value = float(data["value"])
    except (TypeError, ValueError) as exc: raise ParseError("Please provide a valid numeric value.") from exc
    try:
        return ConversionRequest(value, normalize_unit(str(data["from_unit"])), normalize_unit(str(data["to_unit"])))
    except ConversionError as exc: raise ParseError(str(exc)) from exc


def parse_locally(text: str) -> ConversionRequest:
    """Parse standard English and simple Urdu/Hinglish requests without an API."""
    number = re.search(r"(?<![\w.])[-+]?\d*\.?\d+(?![\w.])", text)
    if not number:
        raise ParseError("What number should I convert? Example: '5 km to miles'.")
    unit_tokens = "|".join(sorted((re.escape(alias) for alias in ALIASES), key=len, reverse=True))
    found = re.findall(rf"(?<![a-zA-Z])({unit_tokens})(?![a-zA-Z])", text.lower())
    if len(found) < 2:
        raise ParseError(f"What units should I use for {number.group()}? Example: '{number.group()} kg to pounds'.")
    return validate_request({"value": number.group(), "from_unit": found[0], "to_unit": found[-1]})
