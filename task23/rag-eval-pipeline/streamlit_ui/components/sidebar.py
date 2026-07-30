"""
components/sidebar.py
---------------------
Full left sidebar:
  - App logo + title
  - New Chat button
  - Conversation search
  - Conversation list (switch / rename / delete)
  - Clear all history
  - Export chat
  - Divider
  - Model selector (placeholder)
  - Theme toggle
  - Settings nav link
  - About section
"""

from __future__ import annotations

from datetime import datetime

import streamlit as st

from utils.session import (
    clear_all_conversations,
    delete_conversation,
    get_active_messages,
    get_setting,
    get_sorted_conversations,
    new_conversation,
    rename_conversation,
    search_conversations,
    set_notification,
    set_page,
    switch_conversation,
    update_setting,
)
from utils.formatters import (
    export_to_bytes_markdown,
    export_to_bytes_txt,
    format_relative_time,
    sanitise_filename,
)

# ── Model options (placeholder – swap for real backend list) ──────────────────
_MODELS: list[str] = [
    "llama-3.1-8b-instant",
    "llama-3.1-70b-versatile",
    "mixtral-8x7b-32768",
    "gemma2-9b-it",
    "gpt-4o-mini  (OpenAI)",
    "gpt-4o       (OpenAI)",
]


def render_sidebar() -> None:
    """Render the entire sidebar. Call once from app.py inside `with st.sidebar:`."""
    with st.sidebar:
        _logo_section()
        _new_chat_button()
        st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
        _search_box()
        _conversation_list()
        st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
        _export_section()
        _clear_history_button()
        st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
        _model_selector()
        _theme_toggle()
        st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
        _settings_link()
        _about_section()


# ─────────────────────────────────────────────────────────────────────────────
# Private helpers
# ─────────────────────────────────────────────────────────────────────────────

def _logo_section() -> None:
    st.markdown(
        """
        <div class="sidebar-logo">
            <span class="logo-icon">🤖</span>
            <div>
                <div class="logo-title">ResearchAI</div>
                <div class="logo-sub">Multi-Agent Assistant</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _new_chat_button() -> None:
    st.markdown('<div class="sidebar-new-chat-btn">', unsafe_allow_html=True)
    if st.button("＋  New Chat", key="btn_new_chat", use_container_width=True):
        new_conversation()
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


def _search_box() -> None:
    st.markdown('<p class="sidebar-section-label">Search</p>', unsafe_allow_html=True)
    # The widget manages its own value via key="search_query" — never write back
    st.text_input(
        label="search",
        label_visibility="collapsed",
        placeholder="🔍  Search conversations…",
        key="search_query",
    )


def _conversation_list() -> None:
    st.markdown('<p class="sidebar-section-label">Conversations</p>', unsafe_allow_html=True)

    query = st.session_state.get("search_query", "").strip()
    convs = search_conversations(query) if query else get_sorted_conversations()

    if not convs:
        st.markdown(
            '<p style="font-size:0.8rem;color:rgba(255,255,255,0.3);padding:6px 4px;">'
            "No conversations yet.</p>",
            unsafe_allow_html=True,
        )
        return

    active_id = st.session_state.get("active_conv_id")
    rename_id = st.session_state.get("rename_conv_id")

    for conv in convs:
        cid     = conv["id"]
        title   = conv["title"]
        updated = conv["updated"]
        is_active = cid == active_id

        # ── Rename mode ──────────────────────────────────────────────────────
        if rename_id == cid:
            new_name = st.text_input(
                "Rename",
                value=title,
                key=f"rename_input_{cid}",
                label_visibility="collapsed",
            )
            col_save, col_cancel = st.columns(2)
            with col_save:
                if st.button("✔ Save", key=f"save_{cid}", use_container_width=True):
                    rename_conversation(cid, new_name)
                    st.session_state["rename_conv_id"] = None
                    set_notification("Conversation renamed.", "success")
                    st.rerun()
            with col_cancel:
                if st.button("✖ Cancel", key=f"cancel_{cid}", use_container_width=True):
                    st.session_state["rename_conv_id"] = None
                    st.rerun()
            continue

        # ── Normal row ───────────────────────────────────────────────────────
        active_cls = "active" if is_active else ""
        rel_time   = format_relative_time(updated)

        st.markdown(
            f"""
            <div class="conv-item {active_cls}">
                <span class="conv-title" title="{title}">
                    {"💬" if is_active else "🗨️"} {title}
                </span>
                <span class="conv-time">{rel_time}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Action row: Select / Rename / Delete
        col_sel, col_ren, col_del = st.columns([3, 1, 1])
        with col_sel:
            label = "▶ Open" if not is_active else "✓ Active"
            if st.button(label, key=f"sel_{cid}", use_container_width=True, disabled=is_active):
                switch_conversation(cid)
                st.rerun()
        with col_ren:
            if st.button("✏", key=f"ren_{cid}", help="Rename"):
                st.session_state["rename_conv_id"] = cid
                st.rerun()
        with col_del:
            if st.button("🗑", key=f"del_{cid}", help="Delete"):
                delete_conversation(cid)
                set_notification("Conversation deleted.", "warn")
                st.rerun()


def _export_section() -> None:
    st.markdown('<p class="sidebar-section-label">Export Chat</p>', unsafe_allow_html=True)

    messages = get_active_messages()
    active_conv = st.session_state.conversations.get(
        st.session_state.get("active_conv_id", ""), {}
    )
    title = active_conv.get("title", "chat_export")
    safe_name = sanitise_filename(title)

    if not messages:
        st.markdown(
            '<p style="font-size:0.78rem;color:rgba(255,255,255,0.3);">'
            "No messages to export.</p>",
            unsafe_allow_html=True,
        )
        return

    col_md, col_txt = st.columns(2)
    with col_md:
        st.download_button(
            label="⬇ MD",
            data=export_to_bytes_markdown(messages, title),
            file_name=f"{safe_name}.md",
            mime="text/markdown",
            use_container_width=True,
            key="dl_md",
        )
    with col_txt:
        st.download_button(
            label="⬇ TXT",
            data=export_to_bytes_txt(messages),
            file_name=f"{safe_name}.txt",
            mime="text/plain",
            use_container_width=True,
            key="dl_txt",
        )

    # JSON export on its own row
    from utils.formatters import export_to_bytes_json
    st.download_button(
        label="⬇ JSON",
        data=export_to_bytes_json(messages, title),
        file_name=f"{safe_name}.json",
        mime="application/json",
        use_container_width=True,
        key="dl_json",
    )

    # PDF / DOCX — try dynamic imports, show tooltip if unavailable
    col_pdf, col_docx = st.columns(2)
    with col_pdf:
        from utils.formatters import export_to_bytes_pdf
        pdf_bytes = export_to_bytes_pdf(messages, title)
        if pdf_bytes:
            st.download_button(
                "⬇ PDF", data=pdf_bytes,
                file_name=f"{safe_name}.pdf", mime="application/pdf",
                use_container_width=True, key="dl_pdf",
            )
        else:
            st.button("⬇ PDF", disabled=True, use_container_width=True,
                      help="Install reportlab to enable PDF export", key="dl_pdf_dis")
    with col_docx:
        from utils.formatters import export_to_bytes_docx
        docx_bytes = export_to_bytes_docx(messages, title)
        if docx_bytes:
            st.download_button(
                "⬇ DOCX", data=docx_bytes,
                file_name=f"{safe_name}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True, key="dl_docx",
            )
        else:
            st.button("⬇ DOCX", disabled=True, use_container_width=True,
                      help="Install python-docx to enable DOCX export", key="dl_docx_dis")


def _clear_history_button() -> None:
    if st.button("🗑  Clear All History", key="btn_clear_all", use_container_width=True):
        if st.session_state.get("confirm_clear"):
            clear_all_conversations()
            st.session_state.confirm_clear = False
            set_notification("All conversations cleared.", "warn")
            st.rerun()
        else:
            st.session_state.confirm_clear = True
            st.rerun()

    if st.session_state.get("confirm_clear"):
        st.warning("Click again to confirm clearing all history.")


def _model_selector() -> None:
    st.markdown('<p class="sidebar-section-label">Model</p>', unsafe_allow_html=True)
    current = get_setting("model") or _MODELS[0]
    idx = _MODELS.index(current) if current in _MODELS else 0
    selected = st.selectbox(
        label="model_select",
        label_visibility="collapsed",
        options=_MODELS,
        index=idx,
        key="sb_model",
    )
    update_setting("model", selected)


def _theme_toggle() -> None:
    dark = get_setting("dark_mode")
    label = "☀️  Light Mode" if dark else "🌙  Dark Mode"
    if st.button(label, key="btn_theme", use_container_width=True):
        update_setting("dark_mode", not dark)
        st.rerun()


def _settings_link() -> None:
    if st.button("⚙️  Settings", key="btn_settings_nav", use_container_width=True):
        set_page("settings")
        st.rerun()


def _about_section() -> None:
    with st.expander("ℹ️  About", expanded=False):
        st.markdown(
            """
            <div style="font-size:0.8rem;color:rgba(255,255,255,0.55);line-height:1.6;">
                <b style="color:rgba(255,255,255,0.85);">ResearchAI</b><br>
                Multi-Agent Research Assistant<br><br>
                <b>Agents:</b> Researcher · Writer · Editor<br>
                <b>Backend:</b> LangGraph + RAG Pipeline<br>
                <b>Version:</b> 1.0.0-beta<br><br>
                Built with ❤️ using Streamlit
            </div>
            """,
            unsafe_allow_html=True,
        )
