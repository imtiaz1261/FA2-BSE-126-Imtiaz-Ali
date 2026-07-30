"""
pages/settings.py
-----------------
Full settings page rendered inside the main area when
st.session_state.current_page == "settings".

Sections
~~~~~~~~
1. Model & Generation  — model selector, temperature, max tokens, streaming
2. Appearance          — dark mode, font size
3. Backend             — backend selector, API key placeholders
4. Privacy & Cache     — clear cache button
5. About               — version info, links
"""

from __future__ import annotations

import streamlit as st

from utils.session import (
    clear_all_conversations,
    get_setting,
    set_notification,
    set_page,
    update_setting,
)

# ── Available options (placeholders) ─────────────────────────────────────────
_MODELS: list[str] = [
    "llama-3.1-8b-instant",
    "llama-3.1-70b-versatile",
    "mixtral-8x7b-32768",
    "gemma2-9b-it",
    "gpt-4o-mini",
    "gpt-4o",
]

_BACKENDS: list[str] = ["offline", "groq", "openai"]
_FONT_SIZES: list[str] = ["Small", "Medium", "Large"]


# ──────────────────────────────────────────────────────────────────────────────
# Public entry point
# ──────────────────────────────────────────────────────────────────────────────

def render_settings_page() -> None:
    """Render the full settings page. Call from app.py."""
    _header()
    st.markdown("")

    tab_model, tab_appearance, tab_backend, tab_privacy, tab_about = st.tabs([
        "🤖 Model",
        "🎨 Appearance",
        "🔌 Backend",
        "🔒 Privacy",
        "ℹ️ About",
    ])

    with tab_model:
        _section_model()

    with tab_appearance:
        _section_appearance()

    with tab_backend:
        _section_backend()

    with tab_privacy:
        _section_privacy()

    with tab_about:
        _section_about()


# ──────────────────────────────────────────────────────────────────────────────
# Header
# ──────────────────────────────────────────────────────────────────────────────

def _header() -> None:
    col_back, col_title = st.columns([1, 8])
    with col_back:
        if st.button("← Back", key="settings_back"):
            set_page("chat")
            st.rerun()
    with col_title:
        st.markdown(
            '<h2 style="margin:0;font-size:1.4rem;font-weight:700;">⚙️ Settings</h2>',
            unsafe_allow_html=True,
        )


# ──────────────────────────────────────────────────────────────────────────────
# Tab: Model & Generation
# ──────────────────────────────────────────────────────────────────────────────

def _section_model() -> None:
    st.markdown('<div class="section-header">Model & Generation</div>', unsafe_allow_html=True)

    # Model selector
    current_model = get_setting("model") or _MODELS[0]
    model_idx = _MODELS.index(current_model) if current_model in _MODELS else 0
    selected_model = st.selectbox(
        "Language Model",
        options=_MODELS,
        index=model_idx,
        help="Select the LLM used for generation. Groq models are free-tier.",
        key="setting_model",
    )
    update_setting("model", selected_model)

    st.markdown("")

    # Temperature
    temp = float(get_setting("temperature") or 0.7)
    new_temp = st.slider(
        "Temperature",
        min_value=0.0,
        max_value=2.0,
        value=temp,
        step=0.05,
        help="Higher = more creative. Lower = more deterministic. Recommended: 0.5–0.9",
        key="setting_temp",
    )
    update_setting("temperature", new_temp)

    col_l, col_r = st.columns(2)
    with col_l:
        st.caption(f"Current: **{new_temp:.2f}**")
    with col_r:
        preset_cols = st.columns(3)
        for label, val, col in zip(
            ["Precise (0.2)", "Balanced (0.7)", "Creative (1.2)"],
            [0.2, 0.7, 1.2],
            preset_cols,
        ):
            with col:
                if st.button(label, key=f"temp_preset_{val}", use_container_width=True):
                    update_setting("temperature", val)
                    st.rerun()

    st.markdown("")

    # Max tokens
    max_tok = int(get_setting("max_tokens") or 2048)
    new_max = st.select_slider(
        "Max Output Tokens",
        options=[256, 512, 1024, 2048, 4096, 8192],
        value=max_tok,
        help="Maximum number of tokens the model will generate.",
        key="setting_max_tokens",
    )
    update_setting("max_tokens", new_max)

    st.markdown("")

    # Streaming toggle
    streaming = bool(get_setting("streaming"))
    new_stream = st.toggle(
        "Enable Streaming",
        value=streaming,
        help="Stream the response word-by-word for a real-time feel.",
        key="setting_streaming",
    )
    update_setting("streaming", new_stream)

    st.info(
        "💡 **Tip:** Streaming requires a compatible backend. "
        "In offline mode it is simulated.",
        icon=None,
    )


# ──────────────────────────────────────────────────────────────────────────────
# Tab: Appearance
# ──────────────────────────────────────────────────────────────────────────────

def _section_appearance() -> None:
    st.markdown('<div class="section-header">Appearance</div>', unsafe_allow_html=True)

    # Dark mode
    dark = bool(get_setting("dark_mode"))
    new_dark = st.toggle(
        "Dark Mode",
        value=dark,
        help="Switch between dark and light interface themes.",
        key="setting_dark_mode",
    )
    if new_dark != dark:
        update_setting("dark_mode", new_dark)
        st.rerun()

    st.markdown("")

    # Font size
    font_size = get_setting("font_size") or "Medium"
    fs_idx = _FONT_SIZES.index(font_size) if font_size in _FONT_SIZES else 1
    new_fs = st.radio(
        "Font Size",
        options=_FONT_SIZES,
        index=fs_idx,
        horizontal=True,
        help="Adjust the chat message text size.",
        key="setting_font_size",
    )
    update_setting("font_size", new_fs)

    st.markdown("")

    # Colour palette preview
    st.markdown(
        '<div class="section-header" style="font-size:0.9rem;">Colour Palette Preview</div>',
        unsafe_allow_html=True,
    )
    swatches = [
        ("#10a37f", "Accent"),
        ("#6366f1", "Agent"),
        ("#ef4444", "Error"),
        ("#f59e0b", "Warning"),
        ("#1a1a2e", "Dark BG"),
        ("#ffffff", "Light BG"),
    ]
    cols = st.columns(len(swatches))
    for col, (color, label) in zip(cols, swatches):
        with col:
            st.markdown(
                f"""
                <div style="background:{color};height:36px;border-radius:6px;
                            border:1px solid var(--border-color);margin-bottom:4px;">
                </div>
                <div style="font-size:0.7rem;text-align:center;
                            color:var(--text-secondary);">{label}</div>
                """,
                unsafe_allow_html=True,
            )


# ──────────────────────────────────────────────────────────────────────────────
# Tab: Backend
# ──────────────────────────────────────────────────────────────────────────────

def _section_backend() -> None:
    st.markdown('<div class="section-header">Backend Configuration</div>', unsafe_allow_html=True)

    current_backend = get_setting("backend") or "offline"
    backend_idx = _BACKENDS.index(current_backend) if current_backend in _BACKENDS else 0
    new_backend = st.selectbox(
        "Backend Mode",
        options=_BACKENDS,
        index=backend_idx,
        help=(
            "**offline** — no API key needed, heuristic responses.\n\n"
            "**groq** — free Groq LLM (requires GROQ_API_KEY).\n\n"
            "**openai** — OpenAI GPT models (requires OPENAI_API_KEY)."
        ),
        key="setting_backend",
    )
    update_setting("backend", new_backend)

    st.markdown("")

    # API key inputs (masked, placeholder only — keys should live in .env)
    if new_backend == "groq":
        st.text_input(
            "GROQ_API_KEY",
            type="password",
            placeholder="gsk_…  (set in .env, not stored here)",
            disabled=True,
            help="Set GROQ_API_KEY in your .env file. This field is display-only.",
            key="setting_groq_key",
        )
        st.caption("Get a free key at [console.groq.com](https://console.groq.com/keys)")

    elif new_backend == "openai":
        st.text_input(
            "OPENAI_API_KEY",
            type="password",
            placeholder="sk-…  (set in .env, not stored here)",
            disabled=True,
            help="Set OPENAI_API_KEY in your .env file. This field is display-only.",
            key="setting_openai_key",
        )
        st.caption("Get a key at [platform.openai.com](https://platform.openai.com/api-keys)")

    else:
        st.success("✅ Offline mode — no API key required.")

    st.markdown("")

    # Retrieval settings (placeholder)
    st.markdown(
        '<div class="section-header" style="font-size:0.9rem;">Retrieval Settings</div>',
        unsafe_allow_html=True,
    )
    st.slider(
        "Top-K Chunks",
        min_value=1, max_value=10, value=3,
        help="Number of document chunks retrieved per query.",
        key="setting_top_k",
        disabled=True,
    )
    st.caption("Advanced retrieval settings will be available when backend is connected.")


# ──────────────────────────────────────────────────────────────────────────────
# Tab: Privacy & Cache
# ──────────────────────────────────────────────────────────────────────────────

def _section_privacy() -> None:
    st.markdown('<div class="section-header">Privacy & Data</div>', unsafe_allow_html=True)

    st.markdown(
        """
        <div style="background:var(--bg-secondary);border:1px solid var(--border-color);
                    border-radius:var(--radius-md);padding:14px 16px;font-size:0.875rem;
                    line-height:1.7;color:var(--text-primary);">
            <b>Data storage:</b> All conversations are stored only in your browser session.
            Nothing is sent to external servers unless you configure a live backend.<br><br>
            <b>API keys:</b> Keys are read from the <code>.env</code> file and are
            never transmitted to the UI or stored in session state.<br><br>
            <b>Logs:</b> Pipeline logs are written to <code>logs/pipeline.log</code>
            on your local machine only.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("")

    # Clear cache
    st.markdown(
        '<div class="section-header" style="font-size:0.9rem;">Clear Data</div>',
        unsafe_allow_html=True,
    )

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button(
            "🗑  Clear All Conversations",
            key="settings_clear_convs",
            use_container_width=True,
        ):
            if st.session_state.get("confirm_clear_settings"):
                clear_all_conversations()
                st.session_state["confirm_clear_settings"] = False
                set_notification("All conversations cleared.", "warn")
                st.rerun()
            else:
                st.session_state["confirm_clear_settings"] = True
                st.rerun()

        if st.session_state.get("confirm_clear_settings"):
            st.warning("Click again to confirm.")

    with col_b:
        if st.button(
            "🔄  Reset Settings",
            key="settings_reset",
            use_container_width=True,
        ):
            from utils.session import _DEFAULT_SETTINGS  # type: ignore[attr-defined]
            st.session_state["settings"] = _DEFAULT_SETTINGS.copy()
            set_notification("Settings reset to defaults.", "success")
            st.rerun()

    st.markdown("")
    st.button(
        "🧹  Clear Streamlit Cache",
        key="settings_clear_cache",
        use_container_width=False,
        on_click=st.cache_data.clear,
        help="Clears all @st.cache_data entries.",
    )


# ──────────────────────────────────────────────────────────────────────────────
# Tab: About
# ──────────────────────────────────────────────────────────────────────────────

def _section_about() -> None:
    st.markdown('<div class="section-header">About ResearchAI</div>', unsafe_allow_html=True)

    st.markdown(
        """
        <div style="background:var(--bg-secondary);border:1px solid var(--border-color);
                    border-radius:var(--radius-md);padding:20px;line-height:1.8;">
            <div style="font-size:2.5rem;margin-bottom:8px;">🤖</div>
            <h3 style="margin:0 0 4px;font-size:1.2rem;">ResearchAI</h3>
            <p style="color:var(--text-secondary);font-size:0.85rem;margin:0 0 16px;">
                Multi-Agent Research Assistant
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    info_rows = [
        ("Version",      "1.0.0-beta"),
        ("Framework",    "Streamlit"),
        ("Orchestration","LangGraph"),
        ("Retrieval",    "FAISS + ChromaDB"),
        ("Evaluation",   "RAGAS"),
        ("Embeddings",   "sentence-transformers"),
        ("License",      "MIT"),
    ]

    for label, value in info_rows:
        st.markdown(
            f"""
            <div class="info-row">
                <span class="info-label">{label}</span>
                <span class="info-value">{value}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.link_button("📖 Docs",      "https://docs.streamlit.io",       use_container_width=True)
    with col2:
        st.link_button("🦜 LangGraph", "https://langchain-ai.github.io/langgraph/", use_container_width=True)
    with col3:
        st.link_button("📊 RAGAS",     "https://docs.ragas.io",           use_container_width=True)
