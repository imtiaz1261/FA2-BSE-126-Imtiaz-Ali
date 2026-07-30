"""
utils/formatters.py
-------------------
Pure, stateless formatting helpers used by UI components.

No Streamlit imports here — keep this module testable in isolation.
"""

from __future__ import annotations

import html
import re
from datetime import datetime, timezone


# ── Timestamp ─────────────────────────────────────────────────────────────────

def format_timestamp(iso: str, short: bool = False) -> str:
    """
    Convert an ISO-8601 timestamp string to a human-friendly label.

    Parameters
    ----------
    iso   : str  e.g. "2024-07-27T14:30:00+00:00"
    short : bool If True returns "14:30", otherwise "Jul 27, 14:30"

    Returns "—" on parse failure.
    """
    if not iso:
        return "—"
    try:
        dt = datetime.fromisoformat(iso)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        if short:
            return dt.strftime("%H:%M")
        return dt.strftime("%b %d, %H:%M")
    except ValueError:
        return "—"


def relative_time(iso: str) -> str:
    """
    Return a natural-language relative time string, e.g. "3 min ago".

    Falls back to ``format_timestamp(iso)`` on parse failure.
    """
    if not iso:
        return "—"
    try:
        dt = datetime.fromisoformat(iso)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        delta = datetime.now(timezone.utc) - dt
        seconds = int(delta.total_seconds())
        if seconds < 60:
            return "just now"
        if seconds < 3600:
            m = seconds // 60
            return f"{m} min ago"
        if seconds < 86400:
            h = seconds // 3600
            return f"{h}h ago"
        d = seconds // 86400
        return f"{d}d ago"
    except ValueError:
        return format_timestamp(iso)


# ── Text helpers ──────────────────────────────────────────────────────────────

def truncate(text: str, max_len: int = 50) -> str:
    """Truncate *text* to *max_len* chars and append '…' if needed."""
    text = text.strip()
    if len(text) <= max_len:
        return text
    return text[:max_len].rstrip() + "…"


def word_count(text: str) -> int:
    """Return the number of whitespace-separated words in *text*."""
    return len(text.split())


def reading_time(text: str, wpm: int = 200) -> str:
    """
    Estimate reading time.

    Returns a string like "< 1 min" or "3 min read".
    """
    words = word_count(text)
    minutes = max(1, round(words / wpm))
    if minutes < 1:
        return "< 1 min"
    return f"{minutes} min read"


# ── Markdown / HTML helpers ───────────────────────────────────────────────────

_CODE_FENCE_RE = re.compile(r"```(\w*)\n([\s\S]*?)```", re.MULTILINE)
_INLINE_CODE_RE = re.compile(r"`([^`\n]+)`")


def highlight_code_blocks(markdown_text: str) -> str:
    """
    Wrap fenced code blocks in a ``<div class='code-wrapper'>`` so the
    custom CSS can style them independently of Streamlit's own code blocks.

    This is injected as raw HTML via ``st.markdown(..., unsafe_allow_html=True)``.
    """

    def replacer(match: re.Match) -> str:
        lang = match.group(1) or "text"
        code = html.escape(match.group(2))
        return (
            f"<div class='code-wrapper'>"
            f"<div class='code-lang'>{lang}</div>"
            f"<pre><code class='language-{lang}'>{code}</code></pre>"
            f"</div>"
        )

    return _CODE_FENCE_RE.sub(replacer, markdown_text)


def safe_html(text: str) -> str:
    """Escape *text* for safe embedding inside HTML attributes."""
    return html.escape(text, quote=True)


# ── Token / model helpers ─────────────────────────────────────────────────────

def format_token_count(n: int) -> str:
    """Return a compact token count string, e.g. '1.2k' for 1200."""
    if n >= 1_000:
        return f"{n / 1_000:.1f}k"
    return str(n)


def estimated_cost(
    prompt_tokens: int,
    completion_tokens: int,
    model: str = "gpt-4o-mini",
) -> str:
    """
    Return a rough cost estimate string (USD).

    Prices are approximate and subject to change — this is for display
    purposes only.  All prices per 1 million tokens.
    """
    _price_table: dict[str, tuple[float, float]] = {
        "gpt-4o":          (5.00,  15.00),
        "gpt-4o-mini":     (0.15,   0.60),
        "gpt-4-turbo":     (10.00, 30.00),
        "gpt-3.5-turbo":   (0.50,   1.50),
        "gemini-1.5-flash":(0.075,  0.30),
        "gemini-1.5-pro":  (3.50,  10.50),
    }
    prices = _price_table.get(model, (1.00, 3.00))
    cost = (prompt_tokens * prices[0] + completion_tokens * prices[1]) / 1_000_000
    if cost < 0.0001:
        return "< $0.0001"
    return f"≈ ${cost:.4f}"


# ── Conversation label helpers ────────────────────────────────────────────────

def conversation_label(title: str, updated_at: str) -> str:
    """
    Return a two-line sidebar label for a conversation.

    Line 1: truncated title
    Line 2: relative time
    """
    return f"{truncate(title, 36)}\n{relative_time(updated_at)}"


def agent_state_label(state: str) -> tuple[str, str]:
    """
    Map an agent state string to an (emoji, label) tuple for display.

    Parameters
    ----------
    state : str  One of "idle", "running", "done", "error"

    Returns
    -------
    tuple[str, str]  (emoji, human-readable label)
    """
    mapping = {
        "idle":    ("⏸",  "Idle"),
        "running": ("⚙️", "Running…"),
        "done":    ("✅",  "Complete"),
        "error":   ("❌",  "Error"),
    }
    return mapping.get(state, ("❓", state.capitalize()))
