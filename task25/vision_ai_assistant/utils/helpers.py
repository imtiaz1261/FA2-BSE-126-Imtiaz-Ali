"""
utils/helpers.py
================
General-purpose helpers used across the application.

- Text processing (truncation, markdown detection, JSON detection)
- Timestamp formatting
- Streamlit session state management helpers
- Clipboard-to-text helper
- Token estimation
- Misc UI helpers
"""

from __future__ import annotations

import re
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from loguru import logger


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------

def truncate(text: str, max_len: int = 60, suffix: str = "…") -> str:
    """Truncate text to max_len characters, appending suffix if truncated."""
    if len(text) <= max_len:
        return text
    return text[:max_len - len(suffix)] + suffix


def contains_json(text: str) -> bool:
    """Return True if the text contains a JSON object or array."""
    return bool(re.search(r"\{[\s\S]*?\}", text) or re.search(r"\[[\s\S]*?\]", text))


def contains_markdown_table(text: str) -> bool:
    """Return True if the text contains a Markdown table."""
    return bool(re.search(r"\|.+\|.+\|", text))


def is_code_block(text: str) -> bool:
    """Return True if the text contains a markdown code block."""
    return "```" in text


def extract_code_blocks(text: str) -> List[Dict[str, str]]:
    """
    Extract all code blocks from a Markdown string.

    Returns a list of dicts: [{"language": "json", "code": "..."}, ...]
    """
    pattern = r"```(\w*)\n?([\s\S]*?)```"
    blocks  = []
    for match in re.finditer(pattern, text):
        blocks.append({
            "language": match.group(1).lower() or "text",
            "code":     match.group(2).strip(),
        })
    return blocks


def strip_markdown(text: str) -> str:
    """
    Remove common Markdown formatting to produce plain text.
    Useful for TXT export or clipboard copy.
    """
    # Remove headers
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    # Remove bold/italic
    text = re.sub(r"\*{1,3}(.*?)\*{1,3}", r"\1", text)
    text = re.sub(r"_{1,3}(.*?)_{1,3}", r"\1", text)
    # Remove inline code
    text = re.sub(r"`([^`]+)`", r"\1", text)
    # Remove code fences
    text = re.sub(r"```[\s\S]*?```", "[code block]", text)
    # Remove links
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
    # Remove images
    text = re.sub(r"!\[[^\]]*\]\([^\)]+\)", "[image]", text)
    # Collapse multiple blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def estimate_tokens(text: str) -> int:
    """
    Rough token count estimate (1 token ≈ 4 characters for English text).
    Not accurate — use only for budget estimation, not billing.
    """
    return max(1, len(text) // 4)


def word_count(text: str) -> int:
    """Count words in a string."""
    return len(text.split())


# ---------------------------------------------------------------------------
# Timestamp helpers
# ---------------------------------------------------------------------------

def now_utc() -> datetime:
    """Return current UTC datetime (timezone-aware)."""
    return datetime.now(timezone.utc)


def format_timestamp(dt: datetime, fmt: str = "%H:%M") -> str:
    """Format a datetime for UI display."""
    return dt.strftime(fmt)


def format_timestamp_full(dt: datetime) -> str:
    """Full datetime string for tooltips."""
    return dt.strftime("%Y-%m-%d %H:%M:%S UTC")


def time_ago(dt: datetime) -> str:
    """
    Return a human-readable 'time ago' string.
    e.g. "just now", "2 minutes ago", "3 hours ago"
    """
    now   = datetime.now(timezone.utc)
    # Make dt timezone-aware if naive
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    delta = int((now - dt).total_seconds())

    if delta < 10:
        return "just now"
    if delta < 60:
        return f"{delta}s ago"
    if delta < 3600:
        m = delta // 60
        return f"{m} min{'s' if m > 1 else ''} ago"
    if delta < 86400:
        h = delta // 3600
        return f"{h} hour{'s' if h > 1 else ''} ago"
    d = delta // 86400
    return f"{d} day{'s' if d > 1 else ''} ago"


# ---------------------------------------------------------------------------
# Streamlit session state helpers
# ---------------------------------------------------------------------------

def ss_get(key: str, default: Any = None) -> Any:
    """
    Get a value from st.session_state safely.
    Import streamlit lazily to keep this module testable without streamlit.
    """
    try:
        import streamlit as st
        return st.session_state.get(key, default)
    except ImportError:
        return default


def ss_set(key: str, value: Any) -> None:
    """Set a value in st.session_state safely."""
    try:
        import streamlit as st
        st.session_state[key] = value
    except ImportError:
        pass


def ss_init(key: str, default: Any) -> Any:
    """
    Initialise a session_state key with default if not already set.
    Returns the current value.
    """
    try:
        import streamlit as st
        if key not in st.session_state:
            st.session_state[key] = default
        return st.session_state[key]
    except ImportError:
        return default


def ss_delete(key: str) -> None:
    """Delete a key from session_state if it exists."""
    try:
        import streamlit as st
        if key in st.session_state:
            del st.session_state[key]
    except ImportError:
        pass


# ---------------------------------------------------------------------------
# Session state key constants
# (centralised so typos become import errors, not silent bugs)
# ---------------------------------------------------------------------------
class SSKey:
    """Namespace for all session_state keys used across the app."""
    # Core state
    CURRENT_SESSION   = "current_session"
    CURRENT_IMAGE     = "current_image"
    CURRENT_ANALYSIS  = "current_analysis"
    CURRENT_RESULT    = "current_result"
    HISTORY           = "conversation_history"
    ALL_SESSIONS      = "all_sessions"

    # UI state
    SELECTED_MODEL    = "selected_model"
    THEME             = "theme"
    SHOW_SETTINGS     = "show_settings"
    SHOW_ABOUT        = "show_about"
    IS_PROCESSING     = "is_processing"
    IS_STREAMING      = "is_streaming"
    LAST_ERROR        = "last_error"
    API_KEY_INPUT     = "api_key_input"
    API_KEY_VALID     = "api_key_valid"

    # Upload state
    UPLOAD_KEY        = "upload_key"      # increment to reset uploader
    UPLOADED_FILE     = "uploaded_file"

    # Chat
    CHAT_INPUT        = "chat_input"
    PENDING_PROMPT    = "pending_prompt"  # set by prompt cards


# ---------------------------------------------------------------------------
# Number / currency formatting
# ---------------------------------------------------------------------------

def format_currency(value: str, currency: str = "") -> str:
    """
    Clean up a currency string: remove duplicate symbols, normalise spacing.
    e.g. "£ 2,450.75" → "£2,450.75"
    """
    if not value:
        return ""
    value = value.strip()
    if currency and not value.startswith(currency):
        value = f"{currency}{value}"
    return value


def parse_amount(value: str) -> Optional[float]:
    """
    Try to parse a currency string to float.
    Returns None if parsing fails.
    """
    if not value:
        return None
    # Remove currency symbols and thousands separators
    cleaned = re.sub(r"[^\d\.\-]", "", value.replace(",", ""))
    try:
        return float(cleaned)
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Misc UI helpers
# ---------------------------------------------------------------------------

def document_type_badge(doc_type: str) -> str:
    """
    Return an HTML badge for a document type, suitable for st.markdown().
    """
    from config.constants import DOCUMENT_TYPE_ICONS, DOCUMENT_TYPE_LABELS, THEME
    icon  = DOCUMENT_TYPE_ICONS.get(doc_type, "📄")
    label = DOCUMENT_TYPE_LABELS.get(doc_type, doc_type.replace("_", " ").title())
    color = THEME["primary"]
    return (
        f'<span style="background:{color}22; color:{color}; '
        f'padding:2px 10px; border-radius:12px; font-size:0.8rem; '
        f'border:1px solid {color}44;">'
        f'{icon} {label}</span>'
    )


def confidence_badge(confidence: float) -> str:
    """Return a coloured confidence percentage badge HTML."""
    pct = int(confidence * 100)
    if pct >= 85:
        color = "#10b981"   # green
    elif pct >= 60:
        color = "#f59e0b"   # amber
    else:
        color = "#ef4444"   # red
    return (
        f'<span style="background:{color}22; color:{color}; '
        f'padding:2px 8px; border-radius:12px; font-size:0.75rem; '
        f'border:1px solid {color}44;">'
        f'{pct}% confidence</span>'
    )


def spinner_html(message: str = "Processing…") -> str:
    """Return a simple CSS spinner HTML snippet."""
    return f"""
    <div style="display:flex; align-items:center; gap:8px; color:#94a3b8; font-size:0.9rem;">
        <div style="width:16px; height:16px; border:2px solid #6366f1;
                    border-top-color:transparent; border-radius:50%;
                    animation:spin 0.8s linear infinite;"></div>
        {message}
    </div>
    <style>
        @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
    </style>
    """
