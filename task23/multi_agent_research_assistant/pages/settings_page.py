"""
pages/settings_page.py
-----------------------
Full settings page rendered inside the main content area.

Sections
--------
1. Model & Provider
2. Generation parameters (temperature, max tokens, streaming)
3. Appearance (dark mode, font size)
4. Agent pipeline toggles
5. Cache / storage management
6. Keyboard shortcuts reference

All changes persist in ``st.session_state.settings`` via the
``update_setting()`` helper and survive page reruns for the session.
"""

from __future__ import annotations

import streamlit as st

from utils.session import (
    clear_all_conversations,
    get_setting,
    show_notification,
    update_setting,
)


# ── Model options ─────────────────────────────────────────────────────────────

_PROVIDERS: list[str] = ["openai", "gemini", "ollama"]

_MODELS_BY_PROVIDER: dict[str, list[str]] = {
    "openai": [
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4-turbo",
        "gpt-3.5-turbo",
    ],
    "gemini": [
        "gemini-1.5-flash",
        "gemini-1.5-pro",
        "gemini-2.0-flash",
    ],
    "ollama": [
        "llama3",
        "llama3.1",
        "mistral",
        "phi3",
        "codellama",
    ],
}

_FONT_SIZES: list[str] = ["Small", "Medium", "Large"]


# ── Section renderers ─────────────────────────────────────────────────────────

def _section_model() -> None:
    st.markdown("### 🤖 Model & Provider")
    st.caption("Select which LLM backend powers the agents.")

    provider = st.selectbox(
        "Provider",
        options=_PROVIDERS,
        index=_PROVIDERS.index(get_setting("provider") or "openai"),
        key="settings_provider",
        help="OpenAI uses the API key from your .env file.",
    )
    if provider != get_setting("provider"):
        update_setting("provider", provider)
        # Reset model to first option for new provider
        update_setting("model", _MODELS_BY_PROVIDER[provider][0])
        st.rerun()

    model_opts = _MODELS_BY_PROVIDER.get(provider, [])
    current_model = get_setting("model") or model_opts[0]
    if current_model not in model_opts:
        current_model = model_opts[0]

    model = st.selectbox(
        "Model",
        options=model_opts,
        index=model_opts.index(current_model),
        key="settings_model",
    )
    if model != get_setting("model"):
        update_setting("model", model)


def _section_generation() -> None:
    st.markdown("### ⚙️ Generation Parameters")
    st.caption("Adjust how the model generates responses.")

    col1, col2 = st.columns(2)

    with col1:
        temp = st.slider(
            "Temperature",
            min_value=0.0,
            max_value=2.0,
            value=float(get_setting("temperature") or 0.7),
            step=0.05,
            key="settings_temperature",
            help="Higher = more creative / random. Lower = more deterministic.",
        )
        if temp != get_setting("temperature"):
            update_setting("temperature", temp)

    with col2:
        max_tok = st.slider(
            "Max Tokens",
            min_value=256,
            max_value=16384,
            value=int(get_setting("max_tokens") or 4096),
            step=256,
            key="settings_max_tokens",
            help="Maximum tokens in a single response.",
        )
        if max_tok != get_setting("max_tokens"):
            update_setting("max_tokens", max_tok)

    streaming = st.toggle(
        "Enable Streaming",
        value=bool(get_setting("streaming")),
        key="settings_streaming",
        help="Stream tokens as they are generated (requires backend support).",
    )
    if streaming != get_setting("streaming"):
        update_setting("streaming", streaming)


def _section_appearance() -> None:
    st.markdown("### 🎨 Appearance")

    col1, col2 = st.columns(2)

    with col1:
        dark = st.toggle(
            "🌙 Dark Mode",
            value=bool(get_setting("dark_mode")),
            key="settings_dark_mode",
        )
        if dark != get_setting("dark_mode"):
            update_setting("dark_mode", dark)
            st.rerun()

    with col2:
        font_size = st.selectbox(
            "Font Size",
            options=_FONT_SIZES,
            index=_FONT_SIZES.index(get_setting("font_size") or "Medium"),
            key="settings_font_size",
        )
        if font_size != get_setting("font_size"):
            update_setting("font_size", font_size)


def _section_panels() -> None:
    st.markdown("### 🖥️ Interface Panels")

    col1, col2 = st.columns(2)

    with col1:
        show_agent = st.toggle(
            "Agent Progress Panel",
            value=bool(get_setting("show_agent_panel")),
            key="settings_agent_panel",
            help="Show/hide the agent execution status panel.",
        )
        if show_agent != get_setting("show_agent_panel"):
            update_setting("show_agent_panel", show_agent)

    with col2:
        show_info = st.toggle(
            "Workflow Info Panel",
            value=bool(get_setting("show_info_panel")),
            key="settings_info_panel",
            help="Show/hide the right-side workflow info panel.",
        )
        if show_info != get_setting("show_info_panel"):
            update_setting("show_info_panel", show_info)


def _section_cache() -> None:
    st.markdown("### 🗄️ Storage & Cache")

    st.info(
        "Conversation history is stored in browser session memory.  "
        "It resets when you close the tab.",
        icon="ℹ️",
    )

    col1, col2 = st.columns(2)

    with col1:
        n_convs = len(st.session_state.get("conversations", {}))
        n_msgs  = sum(
            len(c.get("messages", []))
            for c in st.session_state.get("conversations", {}).values()
        )
        st.metric("Conversations", n_convs)
        st.metric("Total Messages", n_msgs)

    with col2:
        if st.button(
            "🗑️  Clear All Conversations",
            use_container_width=True,
            key="settings_clear_convs",
        ):
            clear_all_conversations()
            show_notification("All conversations cleared", "info")
            st.rerun()

        if st.button(
            "🔄  Reset All Settings",
            use_container_width=True,
            key="settings_reset",
        ):
            # Restore defaults
            from utils.session import _SETTINGS_DEFAULT  # noqa: PLC0415
            st.session_state.settings = dict(_SETTINGS_DEFAULT)
            show_notification("Settings reset to defaults", "info")
            st.rerun()


def _section_shortcuts() -> None:
    st.markdown("### ⌨️ Keyboard Shortcuts")
    shortcuts = [
        ("Send message",       "Ctrl + Enter"),
        ("New line in input",  "Shift + Enter"),
        ("New chat",           "N  (coming soon)"),
        ("Focus input",        "/ (coming soon)"),
    ]
    for label, key in shortcuts:
        col1, col2 = st.columns([3, 2])
        col1.markdown(f"<span style='font-size:13px;'>{label}</span>", unsafe_allow_html=True)
        col2.markdown(
            f"<kbd style='background:rgba(128,128,128,0.15);border-radius:4px;"
            f"padding:2px 6px;font-size:12px;font-family:monospace;'>{key}</kbd>",
            unsafe_allow_html=True,
        )


# ── Public renderer ───────────────────────────────────────────────────────────

def render_settings_page() -> None:
    """
    Render the full settings page.

    Call from ``app.py`` when ``st.session_state.current_page == 'settings'``.
    """
    # Back navigation
    if st.button("← Back to Chat", key="settings_back"):
        st.session_state.current_page = "chat"
        st.rerun()

    st.markdown("## ⚙️ Settings")
    st.caption("Configure your AI Research Assistant.")
    st.divider()

    _section_model()
    st.divider()

    _section_generation()
    st.divider()

    _section_appearance()
    st.divider()

    _section_panels()
    st.divider()

    _section_cache()
    st.divider()

    _section_shortcuts()
