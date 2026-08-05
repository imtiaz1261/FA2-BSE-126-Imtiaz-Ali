"""
Agent streaming wire protocol — Phase 11.

Converts AgentEvent dicts (from executor.stream_agent) into the
text/plain stream format consumed by the Streamlit frontend.

Wire format (one line per event, each prefixed with a marker so the
client can distinguish agent events from plain text tokens):

    <!--AGENT:{"type":"intent","intent":"tools"}-->
    <!--AGENT:{"type":"tool_call","name":"calculator","arguments":{"expression":"2+2"}}-->
    <!--AGENT:{"type":"tool_result","name":"calculator","result":"4"}-->
    <!--AGENT:{"type":"final","answer":"The answer is 4","iterations":1}-->

Plain text tokens (for a typing effect on the final answer) are emitted
as raw text WITHOUT a marker, consistent with the existing RAG streaming.

The `format_event` and `parse_event` pair allow both sides to encode
and decode without duplicating the marker logic.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Optional, Tuple

_MARKER_PREFIX = "<!--AGENT:"
_MARKER_SUFFIX = "-->"


def format_event(event: Dict[str, Any]) -> str:
    """
    Encode an AgentEvent dict into a wire-protocol string.
    Plain-text token events are returned as raw content.
    """
    if event.get("type") == "token":
        return event.get("content", "")
    return f"{_MARKER_PREFIX}{json.dumps(event, ensure_ascii=False)}{_MARKER_SUFFIX}"


def parse_event(raw: str) -> Tuple[str, Any]:
    """
    Decode a wire-protocol string.

    Returns:
        ("event", dict)  — for <!--AGENT:{...}--> markers
        ("text",  str)   — for plain text
    """
    raw = raw.strip()
    if raw.startswith(_MARKER_PREFIX) and raw.endswith(_MARKER_SUFFIX):
        inner = raw[len(_MARKER_PREFIX) : -len(_MARKER_SUFFIX)]
        try:
            return ("event", json.loads(inner))
        except json.JSONDecodeError:
            return ("text", raw)
    return ("text", raw)


def is_agent_event(raw: str) -> bool:
    return _MARKER_PREFIX in raw


def extract_events_from_buffer(buffer: str) -> Tuple[list, str]:
    """
    Extract all complete <!--AGENT:...-->  markers from a streaming buffer.

    Returns:
        (events, remaining_buffer)
        events is a list of (kind, payload) tuples as per parse_event.
    """
    events = []
    while _MARKER_PREFIX in buffer:
        start = buffer.find(_MARKER_PREFIX)
        end = buffer.find(_MARKER_SUFFIX, start)
        if end == -1:
            # Marker not yet complete — wait for more data
            break
        end += len(_MARKER_SUFFIX)
        text_before = buffer[:start]
        if text_before:
            events.append(("text", text_before))
        marker = buffer[start:end]
        events.append(parse_event(marker))
        buffer = buffer[end:]

    return events, buffer
