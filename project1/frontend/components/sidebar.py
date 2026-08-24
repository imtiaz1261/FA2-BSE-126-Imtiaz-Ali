"""
frontend/components/sidebar.py — Reliable 3D Glassmorphism Sidebar
====================================================================
Avoids :has() CSS hacks. Uses pure Streamlit buttons with per-button
inline style injection keyed on unique widget IDs.
"""

import sys
from pathlib import Path
_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import streamlit as st


# ── sidebar-wide CSS (injected once) ─────────────────────────────────────
_SIDEBAR_CSS = """
<style>
/* ── Sidebar container ── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg,#0d1220 0%,#090d18 100%) !important;
    border-right: 1px solid rgba(255,255,255,0.07) !important;
    min-width: 220px !important;
}
[data-testid="stSidebar"] > div:first-child {
    padding: 0 !important;
    overflow-x: hidden !important;
}

/* ── All sidebar buttons: base reset ── */
[data-testid="stSidebar"] .stButton > button {
    background: transparent !important;
    border: 1px solid transparent !important;
    color: #94a3b8 !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.875rem !important;
    font-weight: 500 !important;
    text-align: left !important;
    padding: 9px 14px !important;
    border-radius: 10px !important;
    width: 100% !important;
    transition: all 0.2s ease !important;
    box-shadow: none !important;
    margin: 0 !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(255,255,255,0.06) !important;
    border-color: rgba(255,255,255,0.09) !important;
    color: #f1f5f9 !important;
    transform: none !important;
    box-shadow: none !important;
}
[data-testid="stSidebar"] .stButton > button:focus {
    box-shadow: none !important;
    outline: none !important;
}

/* ── Active nav item override (via data-active class on parent) ── */
[data-testid="stSidebar"] .nav-active .stButton > button {
    background: rgba(99,102,241,0.16) !important;
    border-color: rgba(99,102,241,0.30) !important;
    color: #a5b4fc !important;
    font-weight: 600 !important;
}

/* ── Section label ── */
.sb-section {
    font-size: 0.65rem;
    font-weight: 700;
    color: #475569;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    padding: 14px 18px 4px;
}

/* ── User card ── */
.sb-user {
    display: flex; align-items: center; gap: 10px;
    padding: 11px 14px; margin: 10px 12px;
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 12px;
}
.sb-avatar {
    width: 36px; height: 36px; border-radius: 50%;
    background: linear-gradient(135deg,#6366f1,#06b6d4);
    display: flex; align-items: center; justify-content: center;
    font-size: 0.875rem; font-weight: 700; color: white;
    flex-shrink: 0;
}
.sb-name  { font-size:0.8125rem;font-weight:600;color:#f1f5f9;
            white-space:nowrap;overflow:hidden;text-overflow:ellipsis; }
.sb-role  { font-size:0.7rem;color:#64748b;margin-top:1px; }
.sb-badge {
    font-size:0.62rem;font-weight:700;padding:2px 8px;
    border-radius:99px;white-space:nowrap;
}
.sb-badge-admin {
    background:rgba(99,102,241,0.18);color:#a5b4fc;
    border:1px solid rgba(99,102,241,0.3);
}
.sb-badge-free {
    background:rgba(59,130,246,0.15);color:#93c5fd;
    border:1px solid rgba(59,130,246,0.3);
}
.sb-badge-pro {
    background:rgba(99,102,241,0.18);color:#a5b4fc;
    border:1px solid rgba(99,102,241,0.3);
}

/* ── Brand ── */
.sb-brand {
    padding: 20px 18px 14px;
    border-bottom: 1px solid rgba(255,255,255,0.07);
}
.sb-logo {
    font-size: 1.25rem; font-weight: 800; letter-spacing: -0.02em;
    background: linear-gradient(135deg,#a5b4fc,#67e8f9);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    background-clip: text;
}
.sb-tagline { font-size:0.65rem;color:#475569;letter-spacing:.07em;margin-top:3px; }

/* ── Footer ── */
.sb-footer {
    padding: 12px 18px;
    border-top: 1px solid rgba(255,255,255,0.07);
    font-size: 0.68rem; color: #334155; text-align: center;
}

/* hide streamlit default button label padding */
[data-testid="stSidebar"] .stButton { margin: 1px 0 !important; }

/* Make button text left-aligned via p tag */
[data-testid="stSidebar"] .stButton > button > div {
    text-align: left !important;
}
</style>
"""


def _nav(icon: str, label: str, page_key: str) -> None:
    """
    Render one nav button. If it is the active page, wrap it in a
    div.nav-active so the CSS rule above highlights it.
    """
    is_active = st.session_state.get("page") == page_key
    full_label = f"{icon}  {label}"

    if is_active:
        # inject a wrapper that CSS can target
        st.markdown('<div class="nav-active">', unsafe_allow_html=True)

    clicked = st.button(full_label, key=f"nav_{page_key}", use_container_width=True)

    if is_active:
        st.markdown("</div>", unsafe_allow_html=True)

    if clicked:
        if page_key == "chat":
            from frontend.utils.session_state import clear_messages
            clear_messages()
            st.session_state.current_conversation_id = None
        st.session_state.page = page_key
        st.rerun()


def render_sidebar() -> None:
    """Render the complete sidebar navigation."""

    with st.sidebar:
        # inject CSS once
        st.markdown(_SIDEBAR_CSS, unsafe_allow_html=True)

        # ── Brand ────────────────────────────────────────────
        st.markdown("""
        <div class="sb-brand">
            <div class="sb-logo">✦ AIHub</div>
            <div class="sb-tagline">INTELLIGENT AI PLATFORM</div>
        </div>
        """, unsafe_allow_html=True)

        # ── User card ─────────────────────────────────────────
        email    = st.session_state.get("user_email") or ""
        name     = st.session_state.get("user_full_name") or email.split("@")[0] or "User"
        role     = st.session_state.get("user_role", "user")
        plan     = st.session_state.get("subscription_tier", "free")
        initials = name[:2].upper()

        if role == "admin":
            badge = '<span class="sb-badge sb-badge-admin">Admin</span>'
            role_label = "Administrator"
        elif plan == "pro":
            badge = '<span class="sb-badge sb-badge-pro">Pro</span>'
            role_label = "Pro Plan"
        else:
            badge = '<span class="sb-badge sb-badge-free">Free</span>'
            role_label = "Free Plan"

        st.markdown(f"""
        <div class="sb-user">
            <div class="sb-avatar">{initials}</div>
            <div style="flex:1;min-width:0">
                <div class="sb-name">{name}</div>
                <div class="sb-role">{role_label}</div>
            </div>
            {badge}
        </div>
        """, unsafe_allow_html=True)

        # ── CHAT section ──────────────────────────────────────
        st.markdown('<div class="sb-section">Chat</div>', unsafe_allow_html=True)
        _nav("💬", "New Chat",   "chat")
        _nav("🕐", "History",   "history")

        # ── WORKSPACE section ─────────────────────────────────
        st.markdown('<div class="sb-section">Workspace</div>', unsafe_allow_html=True)
        _nav("📄", "Documents",  "documents")
        _nav("📊", "Usage",      "usage")

        # ── ACCOUNT section ───────────────────────────────────
        st.markdown('<div class="sb-section">Account</div>', unsafe_allow_html=True)
        _nav("💳", "Subscription", "subscription")
        _nav("⚙️", "Settings",     "settings")

        # ── ADMIN section (admin only) ────────────────────────
        if role == "admin":
            st.markdown('<div class="sb-section">Admin</div>', unsafe_allow_html=True)
            _nav("🛡️", "Dashboard", "admin")

        # ── spacer ────────────────────────────────────────────
        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

        # ── theme toggle ──────────────────────────────────────
        is_dark     = st.session_state.get("theme", "dark") == "dark"
        theme_icon  = "☀️" if is_dark else "🌙"
        theme_label = "Light mode" if is_dark else "Dark mode"

        if st.button(f"{theme_icon}  {theme_label}",
                     key="sb_theme", use_container_width=True):
            st.session_state.theme = "light" if is_dark else "dark"
            st.rerun()

        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

        # ── sign out ──────────────────────────────────────────
        if st.button("🚪  Sign out",
                     key="sb_logout", use_container_width=True):
            from frontend.utils.session_state import logout_user
            logout_user()
            st.rerun()

        # ── footer ────────────────────────────────────────────
        st.markdown("""
        <div class="sb-footer">AIHub v0.1.0 &nbsp;·&nbsp; © 2026</div>
        """, unsafe_allow_html=True)
