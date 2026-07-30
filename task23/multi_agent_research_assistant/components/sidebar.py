"""
components/sidebar.py
---------------------
Full left sidebar component.

Sections (top → bottom)
------------------------
1. Logo + app title
2. New Chat button
3. Search conversations
4. Conversation history list (active, rename, delete)
5. Export section
6. Settings shortcut / theme toggle
7. About link
"""

from __future__ import annotations

import streamlit as st

from utils.export import EXPORT_OPTIONS
from utils.formatters import relative_time, truncate
from utils.session import (
    clear_all_conversations,
    create_conversation,
    delete_conversation,
    get_active_messages,
    get_active_conversation,
    rename_conversation,
    show_notification,
    update_setting,
    get_setting,
)


# ── Internal helpers ──────────────────────────────────────────────────────────

def _sorted_conversations() -> list[dict]:
    """Return conversations sorted by updated_at descending."""
    convs = list(st.session_state.conversations.values())
    return sorted(convs, key=lambda c: c.get("updated_at", ""), reverse=True)


def _new_chat() -> None:
    """Create a new conversation and switch to chat page."""
    create_conversation()
    st.session_state.current_page = "chat"


def _switch_to(conv_id: str) -> None:
    st.session_state.active_conversation_id = conv_id
    st.session_state.current_page = "chat"
    st.session_state.renaming_conv_id = None


# ── Sub-sections ──────────────────────────────────────────────────────────────

def _render_logo() -> None:
    st.markdown(
        """
        <div style="display:flex;align-items:center;gap:10px;padding:0.5rem 0 1rem;">
            <div style="font-size:28px;">🤖</div>
            <div>
                <div style="font-weight:700;font-size:15px;line-height:1.2;">
                    AI Research Assistant
                </div>
                <div style="font-size:11px;opacity:0.55;">Multi-Agent System</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_new_chat_button() -> None:
    if st.button("➕  New Chat", key="btn_new_chat", use_container_width=True, type="primary"):
        _new_chat()
        st.rerun()


def _render_search() -> None:
    st.session_state.search_query = st.text_input(
        label="search_conversations",
        value=st.session_state.get("search_query", ""),
        placeholder="🔍  Search conversations…",
        label_visibility="collapsed",
        key="sidebar_search",
    )


def _render_conversation_list() -> None:
    """Render the scrollable conversation history."""
    query = st.session_state.get("search_query", "").lower().strip()
    convs = _sorted_conversations()

    if query:
        convs = [c for c in convs if query in c["title"].lower()]

    active_id = st.session_state.get("active_conversation_id")
    renaming_id = st.session_state.get("renaming_conv_id")

    if not convs:
        st.markdown(
            "<p style='font-size:12px;opacity:0.45;text-align:center;padding:1rem 0;'>"
            "No conversations yet</p>",
            unsafe_allow_html=True,
        )
        return

    for conv in convs:
        cid = conv["id"]
        is_active = cid == active_id

        # ── Rename mode ──────────────────────────────────────────
        if renaming_id == cid:
            new_title = st.text_input(
                "Rename",
                value=conv["title"],
                key=f"rename_input_{cid}",
                label_visibility="collapsed",
            )
            col_save, col_cancel = st.columns(2)
            with col_save:
                if st.button("Save", key=f"save_rename_{cid}", use_container_width=True):
                    rename_conversation(cid, new_title)
                    st.session_state.renaming_conv_id = None
                    show_notification("Conversation renamed", "success")
                    st.rerun()
            with col_cancel:
                if st.button("Cancel", key=f"cancel_rename_{cid}", use_container_width=True):
                    st.session_state.renaming_conv_id = None
                    st.rerun()
            continue

        # ── Normal row ───────────────────────────────────────────
        bg   = "rgba(16,163,127,0.12)" if is_active else "transparent"
        color = "#10A37F" if is_active else "inherit"
        border = "1px solid rgba(16,163,127,0.4)" if is_active else "1px solid transparent"

        st.markdown(
            f"""
            <div style="
                background:{bg};
                border:{border};
                border-radius:8px;
                padding:0.4rem 0.5rem;
                margin-bottom:2px;
                cursor:pointer;
            ">
                <div style="font-size:13px;font-weight:{'600' if is_active else '400'};
                            color:{color};white-space:nowrap;overflow:hidden;
                            text-overflow:ellipsis;">
                    💬 {truncate(conv['title'], 32)}
                </div>
                <div style="font-size:10px;opacity:0.5;margin-top:1px;">
                    {relative_time(conv.get('updated_at',''))}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Action buttons under the item
        col_sel, col_ren, col_del = st.columns([3, 1, 1])
        with col_sel:
            label = "▶ Active" if is_active else "Open"
            if st.button(label, key=f"open_{cid}", use_container_width=True):
                _switch_to(cid)
                st.rerun()
        with col_ren:
            if st.button("✏️", key=f"ren_{cid}", help="Rename"):
                st.session_state.renaming_conv_id = cid
                st.rerun()
        with col_del:
            if st.button("🗑️", key=f"del_{cid}", help="Delete"):
                st.session_state.deleting_conv_id = cid
                st.rerun()

        # ── Inline delete confirmation ───────────────────────────
        if st.session_state.get("deleting_conv_id") == cid:
            st.warning(f"Delete **{truncate(conv['title'],24)}**?")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("Yes, delete", key=f"confirm_del_{cid}", use_container_width=True):
                    delete_conversation(cid)
                    st.session_state.deleting_conv_id = None
                    show_notification("Conversation deleted", "info")
                    st.rerun()
            with c2:
                if st.button("Cancel", key=f"cancel_del_{cid}", use_container_width=True):
                    st.session_state.deleting_conv_id = None
                    st.rerun()


def _render_export_section() -> None:
    """Download-button row for the active conversation."""
    messages = get_active_messages()
    conv = get_active_conversation()
    title = conv["title"] if conv else "Chat Export"

    with st.expander("📥  Export Chat", expanded=False):
        if not messages:
            st.caption("No messages to export yet.")
            return
        for label, opts in EXPORT_OPTIONS.items():
            try:
                data = opts["fn"](messages, title)
                st.download_button(
                    label=label,
                    data=data,
                    file_name=opts["file_name"],
                    mime=opts["mime"],
                    use_container_width=True,
                    key=f"export_{opts['file_name']}",
                )
            except Exception as exc:  # noqa: BLE001
                st.caption(f"⚠️ {label} unavailable: {exc}")


def _render_settings_section() -> None:
    """Quick-access settings controls inside the sidebar."""
    with st.expander("⚙️  Settings", expanded=False):
        # Theme toggle
        dark = get_setting("dark_mode")
        new_dark = st.toggle("🌙  Dark Mode", value=dark, key="sidebar_dark_toggle")
        if new_dark != dark:
            update_setting("dark_mode", new_dark)
            st.rerun()

        # Panel toggles
        show_agent = get_setting("show_agent_panel")
        new_agent = st.toggle("🤖  Agent Panel", value=show_agent, key="sidebar_agent_toggle")
        if new_agent != show_agent:
            update_setting("show_agent_panel", new_agent)
            st.rerun()

        show_info = get_setting("show_info_panel")
        new_info = st.toggle("ℹ️  Info Panel", value=show_info, key="sidebar_info_toggle")
        if new_info != show_info:
            update_setting("show_info_panel", new_info)
            st.rerun()

        st.divider()

        if st.button("⚙️  Full Settings", use_container_width=True, key="btn_full_settings"):
            st.session_state.current_page = "settings"
            st.rerun()

        if st.button("ℹ️  About", use_container_width=True, key="btn_about"):
            st.session_state.current_page = "about"
            st.rerun()


def _render_danger_zone() -> None:
    """Clear all conversations — placed at the very bottom."""
    with st.expander("⚠️  Danger Zone", expanded=False):
        st.caption("This will permanently delete all conversations.")
        if st.button("🗑️  Clear All History", use_container_width=True, key="btn_clear_all"):
            clear_all_conversations()
            show_notification("All conversations cleared", "info")
            st.rerun()


# ── Public entry point ────────────────────────────────────────────────────────

def render_sidebar() -> None:
    """
    Render the full sidebar inside ``st.sidebar``.

    Call once per rerun from ``app.py``.
    """
    with st.sidebar:
        _render_logo()
        _render_new_chat_button()

        st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)

        _render_search()

        st.markdown(
            "<p style='font-size:11px;opacity:0.45;margin:0.5rem 0 0.25rem;'>"
            "RECENT CONVERSATIONS</p>",
            unsafe_allow_html=True,
        )

        # Fixed-height scroll region for history
        with st.container(height=340, border=False):
            _render_conversation_list()

        st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)

        _render_export_section()
        _render_settings_section()
        _render_danger_zone()

        # App version footer
        st.markdown(
            "<p style='font-size:10px;opacity:0.3;text-align:center;"
            "position:absolute;bottom:0.75rem;left:0;right:0;'>"
            "v1.0.0 · Multi-Agent Research</p>",
            unsafe_allow_html=True,
        )
