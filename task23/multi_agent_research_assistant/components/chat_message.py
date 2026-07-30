"""
components/chat_message.py
--------------------------
Chat message rendering using Streamlit's native ``st.chat_message``.

Two rendering paths
-------------------
1. ``render_conversation(messages)``
   Replays the full history from session state on each rerun.
   Each message uses ``st.chat_message`` for correct bubble alignment.

2. ``stream_assistant_response(token_generator)``
   Called ONCE while the backend is generating — uses
   ``st.write_stream`` to display tokens as they arrive, producing
   the ChatGPT typing effect.  Returns the complete text so callers
   can save it to session state.

Action row
----------
Below each assistant message: 📋 Copy  👍 Like  👎 Dislike  🔄 Regenerate.
These are real Streamlit buttons — no JavaScript required for copy
(we use ``st.code`` block as a convenience fallback).
"""

from __future__ import annotations

from typing import Generator, Iterable

import streamlit as st

from utils.formatters import format_timestamp
from utils.session import set_message_feedback


# ── Streaming renderer ────────────────────────────────────────────────────────

def stream_assistant_response(token_source: str | Iterable[str]) -> str:
    """
    Stream an assistant response token-by-token into a chat bubble.

    Parameters
    ----------
    token_source : str | Iterable[str]
        Either a complete string (displayed word-by-word with a tiny
        delay for the typing effect) or a generator of string chunks
        from the real LLM stream.

    Returns
    -------
    str   The assembled full response text.
    """
    with st.chat_message("assistant", avatar="🤖"):
        if isinstance(token_source, str):
            # Simulate streaming by writing the full text via st.write_stream
            # wrapping it in a generator so write_stream handles it uniformly
            def _char_gen(text: str) -> Generator[str, None, None]:
                import time as _time
                # Chunk by word for a smooth effect without excessive rerenders
                words = text.split(" ")
                for i, word in enumerate(words):
                    yield word + (" " if i < len(words) - 1 else "")
                    _time.sleep(0.012)   # ~80 words/sec typing speed

            full_text = st.write_stream(_char_gen(token_source))
        else:
            # Real generator from LLM — stream directly
            full_text = st.write_stream(token_source)

    return full_text or ""


# ── Single message bubble ─────────────────────────────────────────────────────

def render_message(msg: dict) -> None:
    """
    Render one message using ``st.chat_message``.

    User messages use ``st.chat_message("user")`` which Streamlit
    aligns to the right automatically.
    Assistant messages use ``st.chat_message("assistant")``.

    A compact action row (copy/like/dislike/regenerate) is rendered
    below every assistant message.
    """
    role    = msg["role"]           # "user" | "assistant"
    content = msg["content"]
    msg_id  = msg["id"]
    ts      = format_timestamp(msg.get("timestamp", ""), short=True)
    liked   = msg.get("liked")      # True | False | None

    avatar = "🧑" if role == "user" else "🤖"

    with st.chat_message(role, avatar=avatar):
        # Full Markdown rendering — st.markdown inside chat_message
        # handles headers, bold, italic, tables, code blocks, blockquotes
        st.markdown(content)
        # Subtle timestamp
        st.markdown(
            f"<span style='font-size:10px;opacity:0.38;'>{ts}</span>",
            unsafe_allow_html=True,
        )

    # Action row — only for assistant messages
    if role == "assistant":
        _render_action_row(msg_id, content, liked)


def _render_action_row(msg_id: str, content: str, liked: bool | None) -> None:
    """
    Compact inline action row below an assistant bubble.

    Buttons are tiny (width=40px) to avoid cluttering the layout.
    The row is wrapped in the .msg-actions CSS class so it fades
    in only on hover (via the theme stylesheet).
    """
    st.markdown("<div class='msg-actions'>", unsafe_allow_html=True)

    # Four micro-columns — tight widths, large right spacer
    c1, c2, c3, c4, _ = st.columns([1, 1, 1, 1, 10])

    with c1:
        if st.button(
            "📋",
            key=f"copy_{msg_id}",
            help="Copy response",
            use_container_width=True,
        ):
            # Show full text in an expander so user can copy manually.
            # navigator.clipboard requires user-gesture; st.code is reliable.
            st.session_state[f"show_copy_{msg_id}"] = not st.session_state.get(
                f"show_copy_{msg_id}", False
            )

    with c2:
        icon_like = "👍" if liked is True else "👍"
        if st.button(icon_like, key=f"like_{msg_id}", help="Good response",
                     use_container_width=True):
            set_message_feedback(msg_id, True)
            st.rerun()

    with c3:
        icon_dl = "👎" if liked is False else "👎"
        if st.button(icon_dl, key=f"dislike_{msg_id}", help="Bad response",
                     use_container_width=True):
            set_message_feedback(msg_id, False)
            st.rerun()

    with c4:
        if st.button("🔄", key=f"regen_{msg_id}", help="Regenerate response",
                     use_container_width=True):
            st.session_state.regenerate_trigger = True
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

    # Copy drawer — toggled by the 📋 button above
    if st.session_state.get(f"show_copy_{msg_id}", False):
        with st.expander("📋 Response text (select all → copy)", expanded=True):
            st.code(content, language="markdown")


# ── Full conversation replay ──────────────────────────────────────────────────

def render_conversation(messages: list[dict]) -> None:
    """
    Render the complete conversation history from session state.

    Call this on every rerun BEFORE the chat input widget so that
    messages always appear above the input bar.

    Parameters
    ----------
    messages : list[Message]  Ordered list from session state.
    """
    for msg in messages:
        render_message(msg)
