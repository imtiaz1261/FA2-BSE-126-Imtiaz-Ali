"""
app.py — ResearchAI Streamlit Frontend
=======================================
Main entry point.  Run with:

    streamlit run streamlit_ui/app.py

Layout
------
  ┌─────────────┬──────────────────────────────┬───────────────┐
  │   Sidebar   │        Main chat area         │  Info panel   │
  │  (260 px)   │  (flexible, max 860 px wide)  │  (collapsed)  │
  └─────────────┴──────────────────────────────┴───────────────┘

Page routing
------------
  current_page == "chat"     → chat interface
  current_page == "settings" → settings page
"""

from __future__ import annotations

import sys
import os

# ── Make sure imports resolve when running as `streamlit run streamlit_ui/app.py`
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import streamlit as st

# ── Internal imports ──────────────────────────────────────────────────────────
from styles.theme import get_css
from utils.session import (
    get_active_messages,
    get_setting,
    init_session,
    new_conversation,
    set_notification,
    toggle_info_panel,
)
from components.sidebar import render_sidebar
from components.chat_message import (
    render_message_list,
    render_skeleton_loader,
    render_typing_indicator,
)
from components.agent_panel import render_agent_panel
from components.empty_state import render_empty_state
from components.chat_input import finalize_generation, generate_mock_response, render_chat_input
from components.info_panel import render_info_panel
from pages.settings import render_settings_page


# ──────────────────────────────────────────────────────────────────────────────
# Page config  (must be first Streamlit call)
# ──────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="ResearchAI — Multi-Agent Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help":     "https://docs.streamlit.io",
        "Report a bug": "https://github.com",
        "About":        "ResearchAI — Multi-Agent Research Assistant v1.0",
    },
)


# ──────────────────────────────────────────────────────────────────────────────
# Boot
# ──────────────────────────────────────────────────────────────────────────────

def _boot() -> None:
    """Initialise session state and inject CSS exactly once per rerun."""
    init_session()

    dark_mode = bool(get_setting("dark_mode"))
    st.markdown(get_css(dark_mode=dark_mode), unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────────────
# Notification toast
# ──────────────────────────────────────────────────────────────────────────────

def _render_notification() -> None:
    """Show a transient st.toast if a notification is queued."""
    note = st.session_state.get("notification")
    if not note:
        return

    kind    = note.get("kind", "success")
    message = note.get("message", "")

    if kind == "success":
        st.toast(f"✅  {message}", icon=None)
    elif kind == "error":
        st.toast(f"❌  {message}", icon=None)
    else:
        st.toast(f"⚠️  {message}", icon=None)

    # Clear after display
    st.session_state["notification"] = None


# ──────────────────────────────────────────────────────────────────────────────
# Chat page
# ──────────────────────────────────────────────────────────────────────────────

def _render_chat_page() -> None:
    """Main chat interface layout."""
    messages       = get_active_messages()
    is_generating  = st.session_state.get("is_generating", False)
    show_info      = st.session_state.get("show_info_panel", False)

    # ── Top header bar ───────────────────────────────────────────────────────
    _render_chat_header(messages)

    # ── Body: agent panel (if active) + messages ────────────────────────────
    # Agent panel — only visible while generating or after a run
    agent_statuses = st.session_state.get("agent_statuses", [])
    any_active = any(a["status"] != "idle" for a in agent_statuses)

    if any_active:
        with st.container():
            render_agent_panel(collapsed=False)

    # ── Main content + optional info panel ──────────────────────────────────
    if show_info:
        chat_col, info_col = st.columns([5, 2], gap="medium")
    else:
        chat_col = st.container()
        info_col = None

    with chat_col:
        if not messages and not is_generating:
            render_empty_state()
        else:
            # Render conversation
            render_message_list(
                messages,
                on_regenerate=_handle_regenerate,
            )

            # Typing / skeleton indicator while generating
            if is_generating:
                render_typing_indicator()

    if info_col is not None:
        with info_col:
            render_info_panel()

    # ── Input bar (sticky bottom) ─────────────────────────────────────────────
    user_text = render_chat_input()

    if user_text:
        # ── PLACEHOLDER: call real backend here ──────────────────────────────
        # Replace generate_mock_response() with your actual LangGraph call:
        #   response = your_backend.run(user_text)
        response = generate_mock_response(user_text)
        finalize_generation(response)
        st.rerun()


def _render_chat_header(messages: list) -> None:
    """Slim top bar with conversation title, info-panel toggle, and new-chat shortcut."""
    active_conv = st.session_state.conversations.get(
        st.session_state.get("active_conv_id", ""), {}
    )
    title = active_conv.get("title", "ResearchAI")

    col_title, col_info, col_new = st.columns([7, 1, 1], gap="small")

    with col_title:
        st.markdown(
            f"""
            <div style="padding:10px 0 4px;font-size:1rem;font-weight:600;
                        color:var(--text-primary);white-space:nowrap;
                        overflow:hidden;text-overflow:ellipsis;">
                🤖 {title}
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_info:
        label = "◀ Info" if st.session_state.get("show_info_panel") else "▶ Info"
        if st.button(label, key="btn_toggle_info", use_container_width=True):
            toggle_info_panel()
            st.rerun()

    with col_new:
        if st.button("＋ New", key="hdr_new_chat", use_container_width=True):
            new_conversation()
            st.rerun()

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)


def _handle_regenerate(msg_id: str) -> None:
    """
    Regenerate: find the last user message before this assistant message
    and re-run the generation pipeline.
    """
    from utils.session import get_active_conversation, add_message, reset_agent_statuses

    conv = get_active_conversation()
    if not conv:
        return

    messages = conv["messages"]
    # Remove all messages from the target assistant message onward
    target_idx = next(
        (i for i, m in enumerate(messages) if m["id"] == msg_id), None
    )
    if target_idx is None:
        return

    # Find the preceding user message
    user_msg = None
    for m in reversed(messages[:target_idx]):
        if m["role"] == "user":
            user_msg = m
            break

    if not user_msg:
        return

    # Trim conversation to just before the assistant reply
    conv["messages"] = messages[:target_idx]

    # Re-generate
    reset_agent_statuses()
    response = generate_mock_response(user_msg["content"])
    finalize_generation(response)
    set_notification("Response regenerated.", "success")
    st.rerun()


# ──────────────────────────────────────────────────────────────────────────────
# Main entry
# ──────────────────────────────────────────────────────────────────────────────

def main() -> None:
    _boot()
    _render_notification()
    render_sidebar()

    current_page = st.session_state.get("current_page", "chat")

    if current_page == "settings":
        render_settings_page()
    else:
        _render_chat_page()


if __name__ == "__main__":
    main()
