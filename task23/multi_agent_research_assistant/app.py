"""
app.py
------
Main Streamlit entrypoint — Multi-Agent AI Research Assistant.

Run:
    streamlit run app.py

Chat flow (ChatGPT-style)
--------------------------
1. User submits a query via ``st.chat_input`` (sticky bottom bar).
2. The user message is saved to session state and immediately rendered.
3. ``run_pipeline_with_status()`` shows live ``st.status`` cards for
   each agent (Researcher → Writer → Editor) while the backend runs.
4. The final response is streamed token-by-token into an assistant
   ``st.chat_message`` bubble via ``stream_assistant_response()``.
5. The complete response is saved and the page reruns to show actions.

Backend integration
-------------------
All backend logic is isolated in ``_call_backend(query)``.
Replace its body with your LangGraph call — everything else stays.
Search for ``# ── BACKEND HOOK ──`` to find the exact line.

Layout
------
┌─────────────┬────────────────────────────────┬────────────────┐
│   Sidebar   │         Chat Area              │  Info Panel    │
│  (always)   │  history → agent panel →       │  (optional)    │
│             │  stream → chat_input (sticky)  │                │
└─────────────┴────────────────────────────────┴────────────────┘
"""

from __future__ import annotations

import time
from typing import Generator

import streamlit as st

# ── Page config — MUST be the very first Streamlit call ──────────────────────
st.set_page_config(
    page_title="AI Research Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get help":     None,
        "Report a bug": None,
        "About":        "Multi-Agent AI Research Assistant v1.0.0",
    },
)

# ── Internal imports (after set_page_config) ─────────────────────────────────
from components.agent_panel    import render_agent_panel, run_pipeline_with_status
from components.chat_input     import render_chat_input
from components.chat_message   import render_conversation, stream_assistant_response
from components.info_panel     import render_info_panel
from components.sidebar        import render_sidebar
from components.welcome_screen import render_welcome_screen
from pages.about_page          import render_about_page
from pages.settings_page       import render_settings_page
from styles.theme              import apply_theme
from utils.session import (
    add_message,
    clear_notification,
    get_active_messages,
    get_setting,
    init_session_state,
    is_dark_mode,
    reset_agent_status,
    reset_workflow_info,
    set_agent_status,
    set_last_user_query,
    show_notification,
    update_workflow_info,
)


# ─────────────────────────────────────────────────────────────────────────────
# BACKEND HOOK — replace _call_backend() to connect your LangGraph pipeline.
# ─────────────────────────────────────────────────────────────────────────────

def _call_backend(query: str) -> str:
    """
    Call the AI backend and return the complete response string.

    # ── BACKEND HOOK ─────────────────────────────────────────────────────────
    Replace the body of this function with your real backend call, e.g.:

        from graph.research_graph import run_research
        result = run_research(query)
        return result["final_response"]

    You can also return a generator for true token-by-token streaming:

        from graph.research_graph import stream_research
        return stream_research(query)   # yields str chunks

    The rest of the app handles both str and Generator[str] transparently.
    # ─────────────────────────────────────────────────────────────────────────
    """
    # ── Mock response (delete when real backend is connected) ─────────────────
    conv_msgs = get_active_messages()
    context_hint = (
        f"\n\n> *Conversation context: {len(conv_msgs)} message(s) in thread.*"
        if len(conv_msgs) > 1 else ""
    )

    return (
        f"## Response to: *{query}*\n\n"
        "This is a **placeholder response** from the mock backend.\n\n"
        "### What the real pipeline will do:\n"
        "1. 🔍 **Researcher** — searches the web with Tavily for up-to-date sources.\n"
        "2. ✍️ **Writer** — drafts a well-structured, comprehensive answer.\n"
        "3. 📝 **Editor** — reviews the draft for accuracy and clarity.\n\n"
        "> Replace `_call_backend()` in `app.py` with your LangGraph call.\n\n"
        "```python\n"
        "# app.py — integration example\n"
        "from graph.research_graph import run_research\n\n"
        "def _call_backend(query: str) -> str:\n"
        "    result = run_research(query)\n"
        "    return result['final_response']\n"
        "```\n\n"
        "**Supported features:**\n"
        "- ✅ Streaming responses (token-by-token)\n"
        "- ✅ Multi-turn conversation memory\n"
        "- ✅ Real-time agent progress indicators\n"
        "- ✅ Export to Markdown / PDF / DOCX / TXT\n"
        "- ✅ Like / Dislike / Regenerate per message\n"
        f"{context_hint}"
    )
    # ── End mock ──────────────────────────────────────────────────────────────


# ─────────────────────────────────────────────────────────────────────────────
# Core processing pipeline
# ─────────────────────────────────────────────────────────────────────────────

def _process_query(user_text: str) -> None:
    """
    Full pipeline for one user turn:

    1. Render the user message immediately.
    2. Run agent pipeline with live ``st.status`` cards.
    3. Stream the response into an assistant bubble.
    4. Persist both messages to session state.
    5. Rerun to refresh sidebar and action buttons.

    Parameters
    ----------
    user_text : str  The cleaned, non-empty user query.
    """
    # Save and display user message right away so it appears before agents run
    set_last_user_query(user_text)
    user_msg = add_message("user", user_text)

    with st.chat_message("user", avatar="🧑"):
        st.markdown(user_text)

    # Mark as processing (disables input)
    st.session_state.is_processing = True
    st.session_state.agent_log = []

    try:
        # ── Live agent pipeline with st.status cards ──────────────────────────
        full_response = run_pipeline_with_status(
            query=user_text,
            backend_fn=_call_backend,
        )

        # ── Stream the response token-by-token ────────────────────────────────
        streamed_text = stream_assistant_response(full_response)

    except Exception as exc:  # noqa: BLE001
        streamed_text = (
            f"⚠️ **An error occurred:**\n\n```\n{exc}\n```\n\n"
            "Please check your backend configuration."
        )
        for agent_key in ("researcher", "writer", "editor"):
            if st.session_state.agent_status.get(agent_key) == "running":
                set_agent_status(agent_key, "error")
        show_notification(f"Error: {exc}", "error")

    finally:
        st.session_state.is_processing = False

    # Persist the assistant message
    add_message("assistant", streamed_text)
    show_notification("Response ready ✓", "success")

    # Rerun so the sidebar updates (new conv title) and action buttons appear
    st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# Page renderers
# ─────────────────────────────────────────────────────────────────────────────

def _render_notification() -> None:
    """Pop any queued toast and clear it."""
    note = st.session_state.get("notification")
    if not note:
        return
    icon_map = {"success": "✅", "error": "❌", "info": "ℹ️"}
    st.toast(note.get("msg", ""), icon=icon_map.get(note.get("type", "info"), "ℹ️"))
    clear_notification()


def _render_chat_page() -> None:
    """
    Main chat page.

    Column layout:
    - If info panel ON  → [chat: 3] [info: 1]
    - If info panel OFF → full-width chat
    """
    show_info  = get_setting("show_info_panel")
    show_agent = get_setting("show_agent_panel")

    if show_info:
        chat_col, info_col = st.columns([3, 1], gap="medium")
    else:
        chat_col = st.container()
        info_col = None

    # ── Chat column ───────────────────────────────────────────────────────────
    with chat_col:
        messages = get_active_messages()

        # Welcome screen when no messages exist
        if not messages:
            render_welcome_screen()
        else:
            # Replay full conversation history
            render_conversation(messages)

        # Agent status summary panel (shown when not mid-processing)
        if show_agent and not st.session_state.get("is_processing", False):
            with st.container(border=True):
                render_agent_panel()

        # ── Sticky input (native st.chat_input) ───────────────────────────────
        user_text = render_chat_input()

        if user_text and not st.session_state.get("is_processing", False):
            _process_query(user_text)

    # ── Info panel column ─────────────────────────────────────────────────────
    if show_info and info_col is not None:
        with info_col:
            render_info_panel()


# ─────────────────────────────────────────────────────────────────────────────
# App entry point
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    """Bootstrap, route, and render."""
    init_session_state()
    apply_theme(dark_mode=is_dark_mode())

    # Sidebar is always rendered regardless of current page
    render_sidebar()

    # Toast notifications
    _render_notification()

    # Route to the correct page
    page = st.session_state.get("current_page", "chat")

    if page == "settings":
        render_settings_page()
    elif page == "about":
        render_about_page()
    else:
        _render_chat_page()


if __name__ == "__main__":
    main()
