"""
Premium Sidebar — Navigation, Usage Meter, Conversations, Documents.
ChatGPT/Claude-inspired collapsible sidebar with full dark theme.
"""
import streamlit as st
from api_client.client import api_client
from components.documents import render_document_manager
from state.session import log_out
from ui_components import plan_badge, kpi_card

MODES = ["Chat", "Knowledge (RAG)", "Research", "Agent"]

_MODE_META = {
    "Chat":           ("💬", "#4f8ef7", "LLM Conversations"),
    "Knowledge (RAG)":("📚", "#8b5cf6", "Document Q&A"),
    "Research":       ("🔬", "#06b6d4", "Deep Web Research"),
    "Agent":          ("🤖", "#10b981", "AI Agent + Tools"),
}

_SIDEBAR_CSS = """
<style>
.sidebar-logo {
    display: flex; align-items: center; gap: 12px;
    padding: 20px 16px 12px;
    border-bottom: 1px solid #1e2d47;
    margin-bottom: 8px;
}
.sidebar-logo-icon {
    width: 38px; height: 38px;
    background: linear-gradient(135deg, #4f8ef7, #7c3aed);
    border-radius: 10px;
    display: flex; align-items: center; justify-content: center;
    font-size: 1.2rem; box-shadow: 0 4px 12px rgba(79,142,247,0.25);
}
.sidebar-logo-text { color: #f0f4ff; font-size: 0.95rem; font-weight: 700; }
.sidebar-logo-sub  { color: #4a5568; font-size: 0.70rem; }

.sidebar-section-label {
    color: #2a3d63; font-size: 0.68rem; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.12em;
    padding: 12px 16px 4px;
}

.sidebar-user {
    display: flex; align-items: center; gap: 10px;
    padding: 12px 16px;
    border-bottom: 1px solid #1e2d47;
    margin-bottom: 8px;
}
.sidebar-avatar {
    width: 34px; height: 34px;
    background: linear-gradient(135deg, #4f8ef7, #7c3aed);
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    color: #fff; font-weight: 700; font-size: 0.85rem; flex-shrink: 0;
}
.sidebar-user-name  { color: #f0f4ff; font-size: 0.88rem; font-weight: 600; }
.sidebar-user-email { color: #4a5568; font-size: 0.72rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 150px; }

.nav-item {
    display: flex; align-items: center; gap: 10px;
    padding: 9px 16px; border-radius: 8px;
    cursor: pointer; transition: all 0.15s ease;
    margin: 2px 8px; color: #64748b; font-size: 0.88rem;
    border: 1px solid transparent;
}
.nav-item:hover {
    background: rgba(79,142,247,0.08);
    border-color: rgba(79,142,247,0.15);
    color: #f0f4ff;
}
.nav-item.active {
    background: rgba(79,142,247,0.12);
    border-color: rgba(79,142,247,0.25);
    color: #f0f4ff;
}

.quota-bar-wrap { padding: 12px 16px; }
.quota-bar-bg {
    background: #1e2d47; border-radius: 4px; height: 5px; margin: 6px 0;
    overflow: hidden;
}
.quota-bar-fill {
    height: 5px; border-radius: 4px;
    transition: width 0.4s ease;
}

.convo-item {
    display: flex; align-items: center; gap: 8px;
    padding: 8px 12px 8px 16px; border-radius: 8px;
    margin: 2px 8px; cursor: pointer;
    transition: all 0.15s ease;
    border: 1px solid transparent;
}
.convo-item:hover {
    background: rgba(79,142,247,0.06);
    border-color: rgba(79,142,247,0.12);
}
.convo-item.active {
    background: rgba(79,142,247,0.1);
    border-color: rgba(79,142,247,0.2);
}
.convo-title {
    color: #94a3b8; font-size: 0.84rem;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    flex: 1;
}
.convo-title.active { color: #f0f4ff; font-weight: 500; }
</style>
"""


def _load_conversations() -> None:
    token  = st.session_state["access_token"]
    result = api_client.list_conversations(token)
    st.session_state["conversations"] = result.data if result.ok else []


def _load_usage() -> None:
    token  = st.session_state["access_token"]
    result = api_client.get_my_usage(token)
    st.session_state["usage_data"] = result.data if result.ok else {}


def _quota_bar(pct: float, label: str) -> str:
    bar_col = "#22c55e" if pct < 70 else ("#f59e0b" if pct < 90 else "#ef4444")
    return (
        f'<div class="quota-bar-wrap">'
        f'<div style="display:flex;justify-content:space-between;'
        f'align-items:center;margin-bottom:4px;">'
        f'<span style="color:#64748b;font-size:0.75rem;">Usage</span>'
        f'<span style="color:{bar_col};font-size:0.75rem;font-weight:600;">'
        f'{pct:.0f}%</span></div>'
        f'<div class="quota-bar-bg">'
        f'<div class="quota-bar-fill" style="width:{min(pct,100):.0f}%;'
        f'background:{bar_col};"></div></div>'
        f'<div style="color:#4a5568;font-size:0.72rem;margin-top:2px;">{label}</div>'
        f'</div>'
    )


def render_sidebar() -> None:
    user = st.session_state.get("user", {})

    with st.sidebar:
        st.markdown(_SIDEBAR_CSS, unsafe_allow_html=True)

        # ── Logo ──────────────────────────────────────────────────────────────
        st.markdown(
            '<div class="sidebar-logo">'
            '<div class="sidebar-logo-icon">🧠</div>'
            '<div><div class="sidebar-logo-text">AI Workspace</div>'
            '<div class="sidebar-logo-sub">Research · RAG · Agents</div></div>'
            '</div>',
            unsafe_allow_html=True,
        )

        # ── User Info ─────────────────────────────────────────────────────────
        name   = user.get("full_name") or user.get("email", "User")
        email  = user.get("email", "")
        plan   = user.get("plan", "free")
        avatar = (name[0].upper() if name else "U")

        st.markdown(
            f'<div class="sidebar-user">'
            f'<div class="sidebar-avatar">{avatar}</div>'
            f'<div style="min-width:0;">'
            f'<div class="sidebar-user-name">{name[:20]}</div>'
            f'<div class="sidebar-user-email">{email}</div>'
            f'</div>'
            f'<div style="margin-left:auto;">'
            + plan_badge(plan, size="sm") +
            '</div></div>',
            unsafe_allow_html=True,
        )

        # ── Top Nav Links ─────────────────────────────────────────────────────
        st.markdown('<div class="sidebar-section-label">Navigation</div>',
                    unsafe_allow_html=True)

        if user.get("is_admin"):
            st.page_link("pages/admin.py",
                         label="🛡️  Admin Dashboard", use_container_width=True)
        st.page_link("pages/usage.py",
                     label="📊  Usage & Billing", use_container_width=True)

        # ── Mode Selector ─────────────────────────────────────────────────────
        st.markdown('<div class="sidebar-section-label">AI Mode</div>',
                    unsafe_allow_html=True)

        usage = st.session_state.get("usage_data", {})
        current_plan = usage.get("plan", plan)

        for mode in MODES:
            icon, col, desc = _MODE_META[mode]
            is_active = st.session_state.get("mode") == mode

            btn_key = f"mode_btn_{mode}"
            if is_active:
                st.markdown(
                    f'<div class="nav-item active" style="border-color:{col}44;'
                    f'background:{col}11;">'
                    f'<span style="color:{col};font-size:1rem;">{icon}</span>'
                    f'<div><div style="color:#f0f4ff;font-size:0.86rem;font-weight:600;">{mode}</div>'
                    f'<div style="color:#4a5568;font-size:0.72rem;">{desc}</div></div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            else:
                if st.button(
                    f"{icon}  {mode}",
                    key=btn_key,
                    use_container_width=True,
                ):
                    st.session_state["mode"] = mode
                    st.rerun()

        # Plan feature hints
        cur_mode = st.session_state.get("mode", "Chat")
        if cur_mode in ("Research", "Agent") and current_plan == "free":
            st.markdown(
                '<div style="margin:4px 16px;padding:8px 12px;'
                'background:rgba(245,158,11,0.08);border:1px solid rgba(245,158,11,0.2);'
                'border-radius:8px;color:#f59e0b;font-size:0.76rem;">⚡ Upgrade to Pro to unlock</div>',
                unsafe_allow_html=True,
            )

        st.divider()

        # ── Conversations ─────────────────────────────────────────────────────
        st.markdown('<div class="sidebar-section-label">Conversations</div>',
                    unsafe_allow_html=True)

        if "conversations" not in st.session_state or not st.session_state["conversations"]:
            _load_conversations()

        new_col1, new_col2 = st.columns([4, 1])
        if new_col1.button("＋  New Chat", use_container_width=True, key="new_chat_btn"):
            token  = st.session_state["access_token"]
            result = api_client.create_conversation(token)
            if result.ok:
                _load_conversations()
                st.session_state["current_conversation_id"] = result.data["id"]
                st.rerun()
            else:
                st.error(result.error)
        if new_col2.button("↻", key="refresh_convos", help="Refresh conversations"):
            _load_conversations()
            st.rerun()

        convos = st.session_state.get("conversations", [])
        if not convos:
            st.markdown(
                '<div style="color:#2a3d63;font-size:0.80rem;text-align:center;'
                'padding:16px 8px;">No conversations yet</div>',
                unsafe_allow_html=True,
            )

        for convo in convos[:30]:
            cid        = convo["id"]
            is_current = cid == st.session_state.get("current_conversation_id")
            title      = convo.get("title", "Conversation")[:35]
            active_cls = "active" if is_current else ""

            cols = st.columns([7, 1, 1])
            with cols[0]:
                btn_label = f"{'▶ ' if is_current else ''}{title}"
                if st.button(btn_label, key=f"sel_{cid}", use_container_width=True):
                    st.session_state["current_conversation_id"] = cid
                    st.rerun()
            with cols[1]:
                if st.button("✎", key=f"ren_{cid}", help="Rename"):
                    st.session_state[f"renaming_{cid}"] = True
            with cols[2]:
                if st.button("✕", key=f"del_{cid}", help="Delete"):
                    token  = st.session_state["access_token"]
                    res    = api_client.delete_conversation(token, cid)
                    if res.ok:
                        if st.session_state.get("current_conversation_id") == cid:
                            st.session_state["current_conversation_id"] = None
                        _load_conversations()
                        st.rerun()

            if st.session_state.get(f"renaming_{cid}"):
                new_title = st.text_input("New title", value=convo["title"],
                                          key=f"newtitle_{cid}")
                c1, c2 = st.columns(2)
                if c1.button("Save", key=f"save_{cid}", type="primary"):
                    token  = st.session_state["access_token"]
                    res    = api_client.rename_conversation(token, cid, new_title)
                    if res.ok:
                        st.session_state[f"renaming_{cid}"] = False
                        _load_conversations()
                        st.rerun()
                if c2.button("Cancel", key=f"canc_{cid}"):
                    st.session_state[f"renaming_{cid}"] = False
                    st.rerun()

        st.divider()

        # ── Usage Quota ───────────────────────────────────────────────────────
        if "usage_data" not in st.session_state:
            _load_usage()

        udata = st.session_state.get("usage_data", {})
        if udata:
            used  = udata.get("monthly_used", 0)
            limit = udata.get("monthly_limit", 100)
            pct   = udata.get("quota_percent", 0.0)
            cost  = udata.get("cost_usd", 0.0)
            remaining = udata.get("monthly_remaining", 0)
            label = f"{remaining:,} remaining · ${cost:.4f}"
            st.markdown(_quota_bar(pct, label), unsafe_allow_html=True)

            if current_plan == "free":
                if st.button("⚡ Upgrade to Pro", use_container_width=True, type="primary",
                             key="sidebar_upgrade"):
                    st.session_state["show_upgrade"] = True
                    st.rerun()

        if st.session_state.get("show_upgrade"):
            _render_upgrade_panel()

        st.divider()

        # ── Documents ─────────────────────────────────────────────────────────
        with st.expander("📄  Knowledge Base", expanded=False):
            render_document_manager()

        # ── Footer ────────────────────────────────────────────────────────────
        st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)
        if st.button("↩  Sign Out", use_container_width=True, key="sign_out_btn"):
            log_out()
            st.rerun()


def _render_upgrade_panel() -> None:
    st.markdown(
        '<div style="background:rgba(124,58,237,0.08);border:1px solid rgba(124,58,237,0.3);'
        'border-radius:12px;padding:16px;margin:8px 0;">'
        '<div style="color:#f0f4ff;font-weight:700;margin-bottom:10px;">⚡ Upgrade Plan</div>'
        '</div>',
        unsafe_allow_html=True,
    )
    choice = st.radio("Plan", ["Pro — $19/mo", "Enterprise — $99/mo"],
                      key="upgrade_radio", label_visibility="collapsed")
    c1, c2 = st.columns(2)
    if c1.button("Upgrade", type="primary", use_container_width=True, key="upgrade_confirm"):
        plan_name = "pro" if "Pro" in choice else "enterprise"
        token     = st.session_state["access_token"]
        res       = api_client.upgrade_plan(token, plan_name)
        if res.ok:
            st.session_state["show_upgrade"] = False
            _load_usage()
            me = api_client.me(token)
            if me.ok:
                st.session_state["user"]["plan"] = me.data.get("plan", plan_name)
            st.success(f"Upgraded to {plan_name.title()}!")
            st.rerun()
        else:
            st.error(res.error)
    if c2.button("Cancel", use_container_width=True, key="upgrade_cancel"):
        st.session_state["show_upgrade"] = False
        st.rerun()
