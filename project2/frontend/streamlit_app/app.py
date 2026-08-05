"""
AI Research Workspace — Premium entrypoint.
ChatGPT/Claude-inspired home with mode cards, theme toggle, and conversation dashboard.
"""
import streamlit as st
from components.auth_forms import render_auth_gate
from components.chat import render_chat
from components.research import render_research
from components.sidebar import render_sidebar
from config import settings
from state.session import init_session_state, is_authenticated
from theme import inject_global_css, inject_page_bg, inject_light_theme, COLORS
from ui_components import kpi_card, section_header, empty_state

st.set_page_config(
    page_title=settings.APP_TITLE,
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Theme Toggle (must be before CSS injection) ───────────────────────────────
if "theme_mode" not in st.session_state:
    st.session_state["theme_mode"] = "dark"

def toggle_theme():
    st.session_state["theme_mode"] = (
        "light" if st.session_state["theme_mode"] == "dark" else "dark"
    )

inject_global_css()
inject_page_bg()
init_session_state()

if not is_authenticated():
    render_auth_gate()
    st.stop()

render_sidebar()

mode = st.session_state.get("mode", "Chat")

_MODE_META = {
    "Chat": ("💬", "#4f8ef7", "LLM Conversations", "Ask anything — I'll answer from my training knowledge."),
    "Knowledge (RAG)": ("📚", "#8b5cf6", "Document Q&A", "Ask questions grounded in your uploaded documents."),
    "Research": ("🔬", "#06b6d4", "Deep Web Research", "I'll search the web, read sources, and write a report."),
    "Agent": ("🤖", "#10b981", "AI Agent + Tools", "I can calculate, search the web, and use tools for you."),
}


def _render_home():
    user = st.session_state.get("user", {})
    name = user.get("full_name") or user.get("email", "there")
    first_name = name.split()[0] if name else "there"

    # Theme toggle in top right
    t_col1, t_col2 = st.columns([8, 1])
    with t_col2:
        theme_icon = "🌙" if st.session_state["theme_mode"] == "light" else "☀️"
        if st.button(theme_icon, key="theme_toggle_home", help="Toggle dark/light mode"):
            toggle_theme()
            st.rerun()

    # Welcome hero
    st.markdown(
        f"""<div style="background:linear-gradient(135deg,#0a0f1e 0%,#0d1535 60%,#111827 100%);
        border:1px solid #1e2d47;border-radius:20px;padding:36px 40px;
        margin-bottom:28px;position:relative;overflow:hidden;">
        <div style="position:absolute;top:-40px;right:-40px;width:200px;height:200px;
        background:radial-gradient(circle,rgba(79,142,247,0.08) 0%,transparent 70%);
        border-radius:50%;"></div>
        <h1 style="color:#f0f4ff;font-size:1.9rem;font-weight:700;margin:0 0 6px;">
        Good day, {first_name}! 👋</h1>
        <p style="color:#64748b;font-size:0.92rem;margin:0;">
        What would you like to explore today?</p>
        </div>""",
        unsafe_allow_html=True,
    )

    # Mode selection cards
    section_header("Choose Your AI Mode", "", "🎯")
    cols = st.columns(4)
    for i, (m, (icon, col, title, desc)) in enumerate(_MODE_META.items()):
        with cols[i]:
            is_active = m == mode
            border = col if is_active else "#1e2d47"
            bg = f"{col}11" if is_active else "#131d32"
            if st.button(
                f"{icon}  {m}",
                key=f"home_mode_{m}",
                use_container_width=True,
                type="primary" if is_active else "secondary",
            ):
                st.session_state["mode"] = m
                st.rerun()
            st.markdown(
                f"""<div style="background:{bg};border:1px solid {border};
                border-radius:12px;padding:14px 16px;margin-top:-8px;">
                <div style="color:{col};font-size:0.78rem;font-weight:600;
                margin-bottom:4px;">{title}</div>
                <div style="color:#4a5568;font-size:0.76rem;line-height:1.5;">{desc}</div>
                </div>""",
                unsafe_allow_html=True,
            )

    st.markdown("<br>", unsafe_allow_html=True)

    # Quick stats
    udata = st.session_state.get("usage_data", {})
    if udata:
        section_header("This Month", "", "📊")
        c1, c2, c3, c4 = st.columns(4)
        kpi_card("Requests", str(udata.get("monthly_used", 0)),
                 f"of {udata.get('monthly_limit', 100)} limit", col=c1)
        kpi_card("Tokens", f"{udata.get('tokens_used', 0):,}", col=c2, accent="#8b5cf6")
        kpi_card("Cost", f"${udata.get('cost_usd', 0):.4f}", col=c3, accent="#f59e0b")
        kpi_card("Remaining", str(udata.get("monthly_remaining", 0)),
                 "requests left", col=c4, accent="#22c55e")

    st.markdown("<br>", unsafe_allow_html=True)

    # Recent conversations
    convos = st.session_state.get("conversations", [])
    if convos:
        section_header("Recent Conversations", "", "💬")
        for convo in convos[:6]:
            cid = convo["id"]
            title = convo.get("title", "Conversation")
            c1, c2 = st.columns([8, 1])
            with c1:
                if st.button(
                    f"💬  {title}",
                    key=f"home_convo_{cid}",
                    use_container_width=True,
                ):
                    st.session_state["current_conversation_id"] = cid
                    st.rerun()
            with c2:
                if st.button("✕", key=f"home_del_{cid}", help="Delete"):
                    from api_client.client import api_client
                    token = st.session_state["access_token"]
                    api_client.delete_conversation(token, cid)
                    from components.sidebar import _load_conversations
                    _load_conversations()
                    st.rerun()
    else:
        empty_state(
            "💬", "Start your first conversation",
            "Create a new chat from the sidebar to begin.",
            "＋ New Conversation",
        )


def _render_chat_page(conversation_id: str, mode: str):
    icon, col, title, desc = _MODE_META.get(mode, ("💬", "#4f8ef7", "Chat", ""))
    convos = st.session_state.get("conversations", [])
    current = next((c for c in convos if c["id"] == conversation_id), None)
    conv_title = current["title"] if current else "Conversation"

    # Theme toggle in top right
    t_col1, t_col2 = st.columns([8, 1])
    with t_col2:
        theme_icon = "🌙" if st.session_state["theme_mode"] == "light" else "☀️"
        if st.button(theme_icon, key="theme_toggle_chat", help="Toggle dark/light mode"):
            toggle_theme()
            st.rerun()

    # Top bar
    tb_l, tb_r = st.columns([7, 2])
    with tb_l:
        st.markdown(
            f"""<div style="display:flex;align-items:center;gap:10px;
            margin-bottom:16px;">
            <span style="background:{col}22;border:1px solid {col}44;
            border-radius:8px;padding:6px 10px;font-size:1.1rem;">{icon}</span>
            <div>
            <div style="color:#f0f4ff;font-weight:700;font-size:1.1rem;">
            {conv_title}</div>
            <div style="color:#4a5568;font-size:0.76rem;">{mode} mode · {desc}</div>
            </div></div>""",
            unsafe_allow_html=True,
        )
    with tb_r:
        if st.button("🏠 Home", key="back_home", use_container_width=True):
            st.session_state["current_conversation_id"] = None
            st.rerun()

    render_chat(conversation_id, mode)


# ── Research is full-page ─────────────────────────────────────────────────────
if mode == "Research":
    render_research()
    st.stop()

# ── Conversation required for Chat / RAG / Agent ──────────────────────────────
conversation_id = st.session_state.get("current_conversation_id")

if conversation_id is None:
    _render_home()
else:
    _render_chat_page(conversation_id, mode)
