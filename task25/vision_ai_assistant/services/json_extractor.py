"""
services/json_extractor.py
===========================
Post-processing pipeline for LLM JSON output.

Responsibilities:
  - Parse raw LLM text into a Python dict
  - Validate against the correct Pydantic extraction schema
  - Clean and normalise field values
  - Handle partial / malformed JSON gracefully
  - Format JSON for display (pretty-printed with syntax highlighting)

This is intentionally kept separate from llm_service.py so that
JSON handling logic can be tested and extended independently.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, Optional, Tuple, Type

from loguru import logger
from pydantic import BaseModel, ValidationError

from models.extraction import get_extraction_schema, GenericExtraction


# ---------------------------------------------------------------------------
# Raw JSON parsing
# ---------------------------------------------------------------------------

def extract_json_from_text(text: str) -> Optional[str]:
    """
    Find and extract a JSON object from a string that may contain
    markdown, prose, or other wrapping text.

    Tries three strategies in order:
      1. Strip ``` fences and parse directly
      2. Find the first { ... } block using brace matching
      3. Find the first [ ... ] block (for arrays)

    Returns:
        The raw JSON string, or None if no valid JSON found.
    """
    if not text:
        return None

    text = text.strip()

    # Strategy 1: strip code fences
    cleaned = _strip_code_fence(text)
    if _is_valid_json(cleaned):
        return cleaned

    # Strategy 2: find balanced braces
    json_str = _extract_balanced(text, "{", "}")
    if json_str and _is_valid_json(json_str):
        return json_str

    # Strategy 3: find balanced brackets (arrays)
    json_str = _extract_balanced(text, "[", "]")
    if json_str and _is_valid_json(json_str):
        return json_str

    # Strategy 4: try to fix common LLM JSON errors then re-parse
    fixed = _attempt_json_repair(cleaned or text)
    if fixed and _is_valid_json(fixed):
        logger.debug("JSON repaired from malformed LLM output")
        return fixed

    return None


def parse_llm_json(text: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Parse LLM output into a Python dict.

    Returns:
        (data_dict, error_message)
        On success: (dict, None)
        On failure: (None, error string)
    """
    json_str = extract_json_from_text(text)

    if not json_str:
        logger.warning("Could not extract JSON from LLM output (len={})", len(text))
        return None, "No valid JSON found in the model response."

    try:
        data = json.loads(json_str)
        if not isinstance(data, dict):
            # Wrap arrays in a dict
            data = {"items": data}
        return data, None
    except json.JSONDecodeError as exc:
        logger.warning("JSON decode error: {}", exc)
        return None, f"JSON parsing error: {exc}"


# ---------------------------------------------------------------------------
# Pydantic validation
# ---------------------------------------------------------------------------

def validate_extraction(
    data: Dict[str, Any],
    document_type: str,
) -> Tuple[Optional[BaseModel], Optional[str]]:
    """
    Validate a parsed dict against the Pydantic schema for document_type.

    Returns:
        (pydantic_model_instance, error_message)
    """
    schema_cls: Type[BaseModel] = get_extraction_schema(document_type)

    try:
        # Use model_validate with strict=False to coerce types where possible
        instance = schema_cls.model_validate(data)
        return instance, None
    except ValidationError as exc:
        # Validation failed — log and fall back to GenericExtraction
        logger.warning(
            "Validation failed for {}: {} errors. Falling back to GenericExtraction.",
            document_type, exc.error_count()
        )
        try:
            generic = GenericExtraction(
                detected_type=document_type,
                all_text=json.dumps(data, indent=2),
                key_value_pairs={k: str(v) for k, v in data.items() if isinstance(v, (str, int, float))},
            )
            return generic, f"Validation warning: {exc.error_count()} field(s) did not match expected schema."
        except Exception:
            return None, str(exc)


# ---------------------------------------------------------------------------
# Full extraction pipeline
# ---------------------------------------------------------------------------

def process_extraction_response(
    llm_output: str,
    document_type: str,
) -> Tuple[Optional[BaseModel], Optional[Dict[str, Any]], Optional[str]]:
    """
    Full pipeline: LLM text → parsed dict → validated Pydantic model.

    Args:
        llm_output:    Raw string from the LLM
        document_type: Document type string (used to select schema)

    Returns:
        (pydantic_instance, raw_dict, error_message)
        All three may be None on total failure.
    """
    # Step 1: Parse JSON
    data, parse_error = parse_llm_json(llm_output)
    if data is None:
        return None, None, parse_error

    # Step 2: Clean nulls and empty collections
    data = _clean_dict(data)

    # Step 3: Validate
    instance, validation_error = validate_extraction(data, document_type)

    return instance, data, validation_error


# ---------------------------------------------------------------------------
# Formatting helpers (for UI display)
# ---------------------------------------------------------------------------

def format_json_for_display(
    data: Dict[str, Any],
    indent: int = 2,
) -> str:
    """
    Return a pretty-printed JSON string, removing None/null values
    for cleaner display.
    """
    cleaned = _remove_nulls(data)
    return json.dumps(cleaned, indent=indent, ensure_ascii=False)


def extraction_to_markdown_table(
    data: Dict[str, Any],
    title: str = "Extracted Information",
) -> str:
    """
    Convert a flat extraction dict to a Markdown table.
    Nested objects / arrays are serialized to compact JSON strings.
    """
    lines = [f"### {title}", "", "| Field | Value |", "|-------|-------|"]

    for key, value in data.items():
        if value is None:
            continue
        label = key.replace("_", " ").title()
        if isinstance(value, (dict, list)):
            cell = f"`{json.dumps(value, ensure_ascii=False)}`"
        else:
            cell = str(value).replace("|", "\\|")
        lines.append(f"| {label} | {cell} |")

    return "\n".join(lines)


def pydantic_to_display_dict(instance: BaseModel) -> Dict[str, Any]:
    """
    Convert a Pydantic model instance to a display-ready dict,
    removing all None values recursively.
    """
    raw = instance.model_dump()
    return _remove_nulls(raw)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _strip_code_fence(text: str) -> str:
    """Remove ``` or ```json wrappers."""
    text = text.strip()
    # Pattern: ```[language]\n...\n```
    match = re.match(r"```(?:json|JSON)?\s*\n?([\s\S]*?)\n?```$", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    # Single-line fence
    if text.startswith("```") and text.endswith("```"):
        return text[3:-3].strip()
    return text


def _is_valid_json(text: str) -> bool:
    try:
        json.loads(text)
        return True
    except (json.JSONDecodeError, TypeError):
        return False


def _extract_balanced(text: str, open_char: str, close_char: str) -> Optional[str]:
    """
    Extract the first balanced open_char...close_char block from text.
    """
    start = text.find(open_char)
    if start == -1:
        return None

    depth  = 0
    in_str = False
    escape = False

    for i, ch in enumerate(text[start:], start):
        if escape:
            escape = False
            continue
        if ch == "\\" and in_str:
            escape = True
            continue
        if ch == '"':
            in_str = not in_str
            continue
        if in_str:
            continue
        if ch == open_char:
            depth += 1
        elif ch == close_char:
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    return None


def _attempt_json_repair(text: str) -> Optional[str]:
    """
    Attempt light repairs on common LLM JSON formatting mistakes:
      - Trailing commas before } or ]
      - Single quotes instead of double quotes
      - Unquoted keys
    """
    # Remove trailing commas
    text = re.sub(r",\s*([}\]])", r"\1", text)
    # Replace single quotes around strings (simple heuristic)
    # Only do this when the entire string looks like it uses single quotes
    if "'" in text and '"' not in text:
        text = text.replace("'", '"')
    return text


def _clean_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively clean a dict:
      - Convert empty strings to None
      - Strip whitespace from string values
      - Remove "N/A", "n/a", "-" placeholder strings (→ None)
    """
    EMPTY_MARKERS = {"n/a", "na", "-", "--", "none", "null", "not available", ""}

    def clean_value(v: Any) -> Any:
        if isinstance(v, str):
            stripped = v.strip()
            if stripped.lower() in EMPTY_MARKERS:
                return None
            return stripped
        if isinstance(v, dict):
            return _clean_dict(v)
        if isinstance(v, list):
            cleaned = [clean_value(item) for item in v]
            return [item for item in cleaned if item is not None]
        return v

    return {k: clean_value(v) for k, v in data.items()}


def _remove_nulls(data: Any) -> Any:
    """Recursively remove None values from dicts and lists."""
    if isinstance(data, dict):
        return {k: _remove_nulls(v) for k, v in data.items() if v is not None}
    if isinstance(data, list):
        cleaned = [_remove_nulls(item) for item in data]
        return [item for item in cleaned if item is not None]
    return data
