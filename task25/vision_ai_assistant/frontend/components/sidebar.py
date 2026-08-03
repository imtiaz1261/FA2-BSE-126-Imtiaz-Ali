"""
frontend/components/sidebar.py
================================
Full left sidebar component.

Renders inside st.sidebar and manages:
  - App logo + branding
  - New Chat button
  - Conversation history list
  - Uploaded images list
  - Settings panel (API key, model, temperature)
  - Export section
  - Clear conversation
  - About section
"""

from __future__ import annotations

from typing import Optional

import streamlit as st

from config.constants import (
    VISION_MODELS, VISION_MODEL_LABELS, THEME,
    APP_ICON, EXPORT_FORMAT_LABELS,
)
from config.settings import get_settings
from utils.helpers import (
    SSKey, ss_get, ss_set, ss_init,
    truncate, time_ago, document_type_badge,
)


# ---------------------------------------------------------------------------
# Main render function
# ---------------------------------------------------------------------------

def render_sidebar() -> None:
    """Render the complete sidebar. Call once per app rerun."""
    with st.sidebar:
        _render_logo()
        st.divider()
        _render_new_chat()
        st.divider()
        _render_history()
        st.divider()
        _render_settings()
        st.divider()
        _render_about()


# ---------------------------------------------------------------------------
# Logo & branding
# ---------------------------------------------------------------------------

def _render_logo() -> None:
    st.markdown(
        f"""
        <div style="text-align:center; padding: 0.5rem 0 0.25rem 0;">
            <div style="font-size:2.2rem;">{APP_ICON}</div>
            <div class="app-logo">Vision AI</div>
            <div class="app-tagline">DOCUMENT UNDERSTANDING ASSISTANT</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# New Chat
# ---------------------------------------------------------------------------

def _render_new_chat() -> None:
    settings = get_settings()
    version  = settings.app_version

    col1, col2 = st.columns([3, 1])
    with col1:
        if st.button(
            "✏️  New Chat",
            use_container_width=True,
            key="btn_new_chat",
            help="Start a new conversation",
        ):
            _start_new_chat()

    with col2:
        st.markdown(
            f'<div style="font-size:0.65rem; color:{THEME["text_muted"]}; '
            f'text-align:right; padding-top:10px;">v{version}</div>',
            unsafe_allow_html=True,
        )


def _start_new_chat() -> None:
    """Save current session to history and reset state."""
    from models.chat import ChatSession
    from utils.helpers import SSKey

    current: Optional[object] = ss_get(SSKey.CURRENT_SESSION)
    if current and hasattr(current, "message_count") and current.message_count > 0:
        _save_session_to_history(current)

    # Reset core state
    ss_set(SSKey.CURRENT_SESSION, ChatSession())
    ss_set(SSKey.CURRENT_IMAGE,    None)
    ss_set(SSKey.CURRENT_ANALYSIS, None)
    ss_set(SSKey.CURRENT_RESULT,   None)
    ss_set(SSKey.IS_PROCESSING,    False)
    ss_set(SSKey.LAST_ERROR,       None)
    # Increment upload key to reset the file uploader widget
    current_key = ss_get(SSKey.UPLOAD_KEY, 0)
    ss_set(SSKey.UPLOAD_KEY, current_key + 1)
    st.rerun()


def _save_session_to_history(session) -> None:
    from models.chat import ConversationHistory
    history: ConversationHistory = ss_get(
        SSKey.HISTORY, ConversationHistory()
    )
    history.add(session)
    ss_set(SSKey.HISTORY, history)
    # Also keep all_sessions dict for restoring
    all_sessions: dict = ss_get(SSKey.ALL_SESSIONS, {})
    all_sessions[session.id] = session
    ss_set(SSKey.ALL_SESSIONS, all_sessions)


# ---------------------------------------------------------------------------
# Conversation history
# ---------------------------------------------------------------------------

def _render_history() -> None:
    from models.chat import ConversationHistory

    st.markdown(
        f'<div style="font-size:0.75rem; color:{THEME["text_muted"]}; '
        f'font-weight:600; letter-spacing:0.5px; margin-bottom:6px;">'
        f'RECENT CHATS</div>',
        unsafe_allow_html=True,
    )

    history: ConversationHistory = ss_get(SSKey.HISTORY, None)

    if not history or not history.sessions:
        st.markdown(
            f'<div style="font-size:0.8rem; color:{THEME["text_muted"]}; '
            f'padding:8px 4px;">No previous chats yet.</div>',
            unsafe_allow_html=True,
        )
        return

    for summary in history.sessions[:8]:   # show last 8
        icon = "🗒️"
        title = truncate(summary.title, 32)
        ago   = time_ago(summary.updated_at)

        col1, col2 = st.columns([5, 1])
        with col1:
            if st.button(
                f"{icon} {title}",
                key=f"history_{summary.session_id}",
                use_container_width=True,
                help=f"Restore: {summary.title}",
            ):
                _restore_session(summary.session_id)
        with col2:
            st.markdown(
                f'<div style="font-size:0.65rem; color:{THEME["text_muted"]}; '
                f'padding-top:10px;">{ago}</div>',
                unsafe_allow_html=True,
            )

    # Clear history button
    if st.button(
        "🗑️ Clear History",
        use_container_width=True,
        key="btn_clear_history",
        help="Remove all conversation history",
    ):
        from models.chat import ConversationHistory
        ss_set(SSKey.HISTORY, ConversationHistory())
        ss_set(SSKey.ALL_SESSIONS, {})
        st.rerun()


def _restore_session(session_id: str) -> None:
    """Restore a previous session from the all_sessions store."""
    all_sessions: dict = ss_get(SSKey.ALL_SESSIONS, {})
    session = all_sessions.get(session_id)
    if session:
        ss_set(SSKey.CURRENT_SESSION, session)
        # Try to restore image if it's still in memory
        st.rerun()


# ---------------------------------------------------------------------------
# Settings panel
# ---------------------------------------------------------------------------

def _render_settings() -> None:
    settings = get_settings()

    with st.expander("⚙️  Settings", expanded=False):

        # --- API Key ---
        st.markdown(
            f'<div style="font-size:0.75rem; color:{THEME["text_muted"]}; '
            f'margin-bottom:4px;">API Key (Groq or OpenAI)</div>',
            unsafe_allow_html=True,
        )

        api_key_valid: bool = ss_get(SSKey.API_KEY_VALID, settings.api_key_configured)

        provider = settings.active_provider.upper() if settings.api_key_configured else "None"
        status_icon  = "✅" if api_key_valid else "⚠️"
        status_text  = f"Connected · {provider}" if api_key_valid else "Not configured"
        status_color = THEME["success"] if api_key_valid else THEME["warning"]

        st.markdown(
            f'<div style="font-size:0.75rem; color:{status_color}; '
            f'margin-bottom:6px;">{status_icon} {status_text}</div>',
            unsafe_allow_html=True,
        )

        new_key = st.text_input(
            "API Key",
            value="",
            type="password",
            placeholder="gsk_... (Groq) or sk-... (OpenAI)",
            label_visibility="collapsed",
            key=SSKey.API_KEY_INPUT,
        )

        if st.button("Apply Key", key="btn_apply_key", use_container_width=True):
            if new_key.strip():
                _apply_api_key(new_key.strip())
            else:
                st.warning("Please enter an API key.")

        st.divider()

        # --- Model selection ---
        st.markdown(
            f'<div style="font-size:0.75rem; color:{THEME["text_muted"]}; '
            f'margin-bottom:4px;">Vision Model</div>',
            unsafe_allow_html=True,
        )

        current_model = ss_get(SSKey.SELECTED_MODEL, settings.default_model)
        model_options = list(VISION_MODEL_LABELS.keys())
        model_labels  = list(VISION_MODEL_LABELS.values())

        try:
            model_idx = model_options.index(current_model)
        except ValueError:
            model_idx = 0

        selected_label = st.selectbox(
            "Model",
            options=model_labels,
            index=model_idx,
            label_visibility="collapsed",
            key="selectbox_model",
        )
        selected_model = model_options[model_labels.index(selected_label)]

        if selected_model != current_model:
            ss_set(SSKey.SELECTED_MODEL, selected_model)
            # Update LLM service if it exists
            llm = ss_get("llm_service")
            if llm:
                llm.model = selected_model

        st.divider()

        # --- Temperature ---
        temp = st.slider(
            "Creativity (Temperature)",
            min_value=0.0,
            max_value=1.5,
            value=float(settings.temperature),
            step=0.05,
            help="Lower = more precise, Higher = more creative",
            key="slider_temperature",
        )
        ss_set("temperature_override", temp)

        st.divider()

        # --- Clear conversation ---
        if st.button(
            "🗑️  Clear Current Chat",
            use_container_width=True,
            key="btn_clear_chat",
        ):
            from models.chat import ChatSession
            ss_set(SSKey.CURRENT_SESSION, ChatSession())
            st.rerun()


def _apply_api_key(key: str) -> None:
    """Validate and apply a new Groq or OpenAI API key at runtime."""
    from services.llm_service import validate_api_key, reset_client
    import os

    with st.spinner("Validating API key…"):
        valid, msg = validate_api_key(key)

    if valid:
        key = key.strip()
        if key.startswith("gsk_"):
            os.environ["GROQ_API_KEY"] = key
        else:
            os.environ["OPENAI_API_KEY"] = key
        reset_client()
        # Clear settings cache so new key is picked up
        from config.settings import get_settings
        get_settings.cache_clear()
        ss_set(SSKey.API_KEY_VALID, True)
        ss_set("llm_service", None)
        ss_set("vision_service", None)
        st.success(f"✅ {msg}")
        st.rerun()
    else:
        ss_set(SSKey.API_KEY_VALID, False)
        st.error(f"❌ {msg}")


# ---------------------------------------------------------------------------
# About section
# ---------------------------------------------------------------------------

def _render_about() -> None:
    with st.expander("ℹ️  About", expanded=False):
        st.markdown(
            f"""
            <div style="font-size:0.82rem; color:{THEME['text_secondary']}; 
                        line-height:1.7;">
                <b style="color:{THEME['primary']};">Vision AI Assistant</b><br>
                Multimodal document understanding powered by GPT-4o Vision.<br><br>
                <b>Supported Documents:</b><br>
                Invoices · Receipts · Bank Statements · Business Cards · 
                Diagrams · Flowcharts · Forms · Handwritten Notes · 
                Medical Reports (Demo) · ID Cards (Demo)<br><br>
                <b>Export Formats:</b><br>
                JSON · Markdown · PDF · DOCX · TXT<br><br>
                <span style="color:{THEME['text_muted']}; font-size:0.75rem;">
                Built with Streamlit + OpenAI Vision API
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )
