"""
components/chat_message.py
--------------------------
Renders individual chat messages (user & assistant) with:
  - Rounded chat bubbles, avatars
  - Timestamp
  - Markdown + code rendering
  - Copy / Like / Dislike / Regenerate action buttons
  - Typing / skeleton loader states
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import streamlit as st

from utils.formatters import format_timestamp
from utils.session import get_active_conversation, set_notification


# ──────────────────────────────────────────────────────────────────────────────
# Public renderers
# ──────────────────────────────────────────────────────────────────────────────

def render_message(msg: dict[str, Any], on_regenerate=None) -> None:
    """
    Render a single message bubble.

    Parameters
    ----------
    msg           : message dict from session state
    on_regenerate : optional callable invoked when user clicks Regenerate
    """
    role      = msg.get("role", "user")
    content   = msg.get("content", "")
    ts        = msg.get("timestamp")
    msg_id    = msg.get("id", "")
    liked     = msg.get("liked")

    ts_str = format_timestamp(ts, short=True) if isinstance(ts, datetime) else ""

    if role == "user":
        _render_user_bubble(content, ts_str, msg_id)
    else:
        _render_assistant_bubble(content, ts_str, msg_id, liked, on_regenerate)


def render_typing_indicator() -> None:
    """Show a three-dot typing animation while the assistant is generating."""
    st.markdown(
        """
        <div class="message-row">
            <div class="avatar ai-avatar">🤖</div>
            <div>
                <div class="typing-indicator">
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                </div>
                <div class="message-meta">Thinking…</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_skeleton_loader() -> None:
    """Show skeleton placeholder lines while streaming content loads."""
    st.markdown(
        """
        <div class="message-row" style="padding:0 16px;max-width:860px;margin:8px auto;">
            <div class="avatar ai-avatar" style="opacity:0.4;">🤖</div>
            <div style="flex:1;max-width:70%;">
                <div class="skeleton long"></div>
                <div class="skeleton medium"></div>
                <div class="skeleton short"></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_message_list(messages: list[dict[str, Any]], on_regenerate=None) -> None:
    """Render every message in *messages* in order."""
    for msg in messages:
        render_message(msg, on_regenerate=on_regenerate)


# ──────────────────────────────────────────────────────────────────────────────
# Private helpers
# ──────────────────────────────────────────────────────────────────────────────

def _render_user_bubble(content: str, ts_str: str, msg_id: str) -> None:
    """Right-aligned user message with U avatar."""
    # Avatar initial from the first word of the model name or just "U"
    initials = "U"

    st.markdown(
        f"""
        <div class="message-row user">
            <div class="avatar user-avatar">{initials}</div>
            <div>
                <div class="bubble user-bubble">{_escape_for_html_attr(content)}</div>
                <div class="message-meta">{ts_str}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Render the actual markdown content using st.markdown for full rendering
    # We use a hidden container trick: render in an expander-free block
    with st.container():
        # Invisible anchor; the bubble HTML above shows the styled shell,
        # but for proper markdown rendering we render it below using st columns
        pass

    # Clean approach: render bubble content natively for markdown support
    _render_bubble_content_user(content, msg_id, ts_str)


def _render_assistant_bubble(
    content: str,
    ts_str: str,
    msg_id: str,
    liked: str | None,
    on_regenerate=None,
) -> None:
    """Left-aligned assistant message with robot avatar and action buttons."""
    _render_bubble_content_assistant(content, msg_id, ts_str, liked, on_regenerate)


def _render_bubble_content_user(content: str, msg_id: str, ts_str: str) -> None:
    """Render user message using Streamlit's native chat_message for proper markdown."""
    with st.chat_message("user"):
        st.markdown(content)
        if ts_str:
            st.caption(ts_str)


def _render_bubble_content_assistant(
    content: str,
    msg_id: str,
    ts_str: str,
    liked: str | None,
    on_regenerate=None,
) -> None:
    """Render assistant message with full markdown support and action bar."""
    with st.chat_message("assistant"):
        st.markdown(content)

        # ── Action bar ──────────────────────────────────────────────────────
        col_ts, col_copy, col_like, col_dislike, col_regen = st.columns(
            [3, 1, 1, 1, 1.5], gap="small"
        )

        with col_ts:
            if ts_str:
                st.caption(ts_str)

        with col_copy:
            if st.button("📋", key=f"copy_{msg_id}", help="Copy response"):
                # Streamlit cannot write to clipboard directly;
                # we use a JS workaround via components or just notify.
                _copy_to_clipboard_js(content, msg_id)
                set_notification("Response copied to clipboard.", "success")
                st.rerun()

        with col_like:
            liked_style = "✅" if liked == "up" else "👍"
            if st.button(liked_style, key=f"like_{msg_id}", help="Good response"):
                _update_message_field(msg_id, "liked", "up")
                st.rerun()

        with col_dislike:
            disliked_style = "❌" if liked == "down" else "👎"
            if st.button(disliked_style, key=f"dislike_{msg_id}", help="Bad response"):
                _update_message_field(msg_id, "liked", "down")
                st.rerun()

        with col_regen:
            if st.button("🔄 Regenerate", key=f"regen_{msg_id}", help="Regenerate response"):
                if on_regenerate:
                    on_regenerate(msg_id)


def _update_message_field(msg_id: str, field: str, value: Any) -> None:
    """Find a message by id in the active conversation and update a field."""
    conv = get_active_conversation()
    if not conv:
        return
    for msg in conv["messages"]:
        if msg.get("id") == msg_id:
            msg[field] = value
            break


def _copy_to_clipboard_js(content: str, msg_id: str) -> None:
    """
    Inject a tiny JS snippet to copy text to the user's clipboard.
    Streamlit allows st.components.v1.html for this purpose.
    """
    import streamlit.components.v1 as components  # lazy import

    # Escape backticks and backslashes for inline JS string
    safe = content.replace("\\", "\\\\").replace("`", "\\`")
    components.html(
        f"""
        <script>
        navigator.clipboard.writeText(`{safe}`)
          .catch(() => {{/* clipboard blocked in some browsers */}});
        </script>
        """,
        height=0,
    )


def _escape_for_html_attr(text: str) -> str:
    """Minimal HTML escaping for tooltip / title attributes."""
    return (
        text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
    )
