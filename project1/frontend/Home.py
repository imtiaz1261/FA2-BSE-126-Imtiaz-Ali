"""
frontend/Home.py — AIHub Main Entry Point
==========================================
Single-page multi-view app with 3D glassmorphism design system.
"""

import sys
from pathlib import Path
_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import streamlit as st

st.set_page_config(
    page_title="AIHub — Intelligent AI Platform",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# GLOBAL 3D GLASSMORPHISM DESIGN SYSTEM
# ============================================================
st.markdown("""
<style>
/* ── Google Font ── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

/* ── CSS Variables ── */
:root {
    --bg-primary:    #0a0e1a;
    --bg-secondary:  #0f1629;
    --bg-card:       rgba(15, 22, 41, 0.85);
    --bg-glass:      rgba(255, 255, 255, 0.04);
    --bg-glass-hover:rgba(255, 255, 255, 0.08);
    --border-glass:  rgba(255, 255, 255, 0.10);
    --border-glow:   rgba(99, 102, 241, 0.45);

    --accent-purple: #6366f1;
    --accent-blue:   #3b82f6;
    --accent-cyan:   #06b6d4;
    --accent-green:  #10b981;
    --accent-orange: #f59e0b;
    --accent-red:    #ef4444;

    --text-primary:  #f1f5f9;
    --text-secondary:#94a3b8;
    --text-muted:    #64748b;

    --shadow-glow:   0 0 40px rgba(99, 102, 241, 0.15);
    --shadow-card:   0 8px 32px rgba(0, 0, 0, 0.4), 0 1px 0 rgba(255,255,255,0.06) inset;
    --shadow-3d:     0 20px 60px rgba(0,0,0,0.5), 0 4px 16px rgba(0,0,0,0.3), 0 1px 0 rgba(255,255,255,0.08) inset;

    --radius-sm:  8px;
    --radius-md:  12px;
    --radius-lg:  16px;
    --radius-xl:  24px;

    --transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

/* ── App background ── */
.stApp, [data-testid="stAppViewContainer"] {
    background: linear-gradient(135deg, #0a0e1a 0%, #0f1629 40%, #0d1424 100%) !important;
    font-family: 'Inter', -apple-system, sans-serif !important;
}
[data-testid="stAppViewContainer"] > .main {
    background: transparent !important;
}
.main .block-container {
    padding: 1.5rem 2rem !important;
    max-width: 1400px !important;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0d1220 0%, #0a0e1a 100%) !important;
    border-right: 1px solid var(--border-glass) !important;
}
[data-testid="stSidebar"] > div {
    padding-top: 0 !important;
}

/* ── All Streamlit buttons → reset base ── */
.stButton > button {
    background: var(--bg-glass) !important;
    border: 1px solid var(--border-glass) !important;
    color: var(--text-secondary) !important;
    border-radius: var(--radius-md) !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.875rem !important;
    font-weight: 500 !important;
    transition: var(--transition) !important;
    backdrop-filter: blur(8px) !important;
}
.stButton > button:hover {
    background: var(--bg-glass-hover) !important;
    border-color: var(--border-glow) !important;
    color: var(--text-primary) !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 20px rgba(99,102,241,0.2) !important;
}
.stButton > button:active {
    transform: translateY(0px) !important;
}

/* ── Primary CTA button (use class .cta via markdown) ── */
button[kind="primary"] {
    background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%) !important;
    border: none !important;
    color: white !important;
    box-shadow: 0 4px 15px rgba(99,102,241,0.4) !important;
}
button[kind="primary"]:hover {
    background: linear-gradient(135deg, #818cf8 0%, #6366f1 100%) !important;
    box-shadow: 0 8px 25px rgba(99,102,241,0.5) !important;
}

/* ── Text inputs ── */
.stTextInput > div > div > input,
.stTextArea textarea {
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid var(--border-glass) !important;
    border-radius: var(--radius-md) !important;
    color: var(--text-primary) !important;
    font-family: 'Inter', sans-serif !important;
    transition: var(--transition) !important;
}
.stTextInput > div > div > input:focus,
.stTextArea textarea:focus {
    border-color: var(--accent-purple) !important;
    box-shadow: 0 0 0 3px rgba(99,102,241,0.15) !important;
}
.stTextInput label, .stTextArea label,
[data-testid="stWidgetLabel"] {
    color: var(--text-secondary) !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.8125rem !important;
    font-weight: 500 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.05em !important;
}

/* ── Selectbox ── */
.stSelectbox > div > div {
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid var(--border-glass) !important;
    border-radius: var(--radius-md) !important;
    color: var(--text-primary) !important;
}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    background: rgba(255,255,255,0.03) !important;
    border-radius: var(--radius-md) !important;
    padding: 4px !important;
    border: 1px solid var(--border-glass) !important;
    gap: 2px !important;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    color: var(--text-muted) !important;
    border-radius: var(--radius-sm) !important;
    font-family: 'Inter', sans-serif !important;
    font-weight: 500 !important;
    font-size: 0.875rem !important;
    transition: var(--transition) !important;
}
.stTabs [aria-selected="true"] {
    background: rgba(99,102,241,0.2) !important;
    color: var(--accent-purple) !important;
    border: none !important;
}

/* ── Metrics ── */
[data-testid="metric-container"] {
    background: var(--bg-glass) !important;
    border: 1px solid var(--border-glass) !important;
    border-radius: var(--radius-lg) !important;
    padding: 1.25rem !important;
    backdrop-filter: blur(12px) !important;
    box-shadow: var(--shadow-card) !important;
    transition: var(--transition) !important;
}
[data-testid="metric-container"]:hover {
    border-color: var(--border-glow) !important;
    box-shadow: var(--shadow-glow) !important;
    transform: translateY(-2px) !important;
}
[data-testid="metric-container"] [data-testid="stMetricLabel"] {
    color: var(--text-muted) !important;
    font-size: 0.75rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.08em !important;
    font-weight: 600 !important;
}
[data-testid="metric-container"] [data-testid="stMetricValue"] {
    color: var(--text-primary) !important;
    font-size: 1.75rem !important;
    font-weight: 700 !important;
}
[data-testid="metric-container"] [data-testid="stMetricDelta"] {
    font-size: 0.8rem !important;
}

/* ── Dataframe ── */
[data-testid="stDataFrame"] {
    border: 1px solid var(--border-glass) !important;
    border-radius: var(--radius-lg) !important;
    overflow: hidden !important;
}

/* ── Progress bar ── */
.stProgress > div > div {
    background: linear-gradient(90deg, var(--accent-purple), var(--accent-cyan)) !important;
    border-radius: 99px !important;
}
.stProgress > div {
    background: rgba(255,255,255,0.06) !important;
    border-radius: 99px !important;
}

/* ── Divider ── */
hr {
    border: none !important;
    border-top: 1px solid var(--border-glass) !important;
    margin: 1rem 0 !important;
}

/* ── Alerts ── */
.stAlert {
    border-radius: var(--radius-md) !important;
    border: 1px solid !important;
    backdrop-filter: blur(8px) !important;
}
[data-baseweb="notification"][data-toast-type="success"] {
    background: rgba(16,185,129,0.12) !important;
    border-color: rgba(16,185,129,0.3) !important;
}
[data-baseweb="notification"][data-toast-type="error"] {
    background: rgba(239,68,68,0.12) !important;
    border-color: rgba(239,68,68,0.3) !important;
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 99px; }
::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.2); }

/* ── Custom component classes ── */
.glass-card {
    background: var(--bg-glass) !important;
    border: 1px solid var(--border-glass);
    border-radius: var(--radius-lg);
    padding: 1.5rem;
    backdrop-filter: blur(16px);
    box-shadow: var(--shadow-card);
    transition: var(--transition);
}
.glass-card:hover {
    border-color: var(--border-glow);
    box-shadow: var(--shadow-3d);
    transform: translateY(-3px);
}

.section-title {
    font-size: 1.5rem;
    font-weight: 700;
    color: var(--text-primary);
    letter-spacing: -0.02em;
    margin: 0 0 0.25rem 0;
}
.section-sub {
    font-size: 0.875rem;
    color: var(--text-muted);
    margin: 0 0 1.5rem 0;
}

.badge {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 2px 10px;
    border-radius: 99px;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.04em;
}
.badge-purple { background: rgba(99,102,241,0.18); color: #a5b4fc; border: 1px solid rgba(99,102,241,0.3); }
.badge-green  { background: rgba(16,185,129,0.15); color: #6ee7b7; border: 1px solid rgba(16,185,129,0.3); }
.badge-orange { background: rgba(245,158,11,0.15); color: #fcd34d; border: 1px solid rgba(245,158,11,0.3); }
.badge-red    { background: rgba(239,68,68,0.15);  color: #fca5a5; border: 1px solid rgba(239,68,68,0.3); }
.badge-blue   { background: rgba(59,130,246,0.15); color: #93c5fd; border: 1px solid rgba(59,130,246,0.3); }

/* ── Sidebar nav item ── */
.nav-item {
    display: flex; align-items: center; gap: 10px;
    padding: 9px 14px; border-radius: var(--radius-md);
    color: var(--text-secondary); font-size: 0.875rem; font-weight: 500;
    cursor: pointer; transition: var(--transition);
    border: 1px solid transparent; margin: 1px 0;
    text-decoration: none;
}
.nav-item:hover {
    background: var(--bg-glass-hover);
    color: var(--text-primary);
    border-color: var(--border-glass);
}
.nav-item.active {
    background: rgba(99,102,241,0.15);
    color: #a5b4fc;
    border-color: rgba(99,102,241,0.25);
}

/* ── Chat messages ── */
.msg-user {
    background: linear-gradient(135deg, #4f46e5 0%, #6366f1 100%);
    color: white; padding: 12px 16px; border-radius: 18px 18px 4px 18px;
    margin: 8px 0; max-width: 75%; margin-left: auto;
    box-shadow: 0 4px 16px rgba(99,102,241,0.3);
    font-size: 0.9375rem; line-height: 1.6;
    word-wrap: break-word;
}
.msg-assistant {
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.09);
    color: var(--text-primary); padding: 12px 16px;
    border-radius: 18px 18px 18px 4px;
    margin: 8px 0; max-width: 75%;
    backdrop-filter: blur(8px);
    font-size: 0.9375rem; line-height: 1.6;
    word-wrap: break-word;
    box-shadow: 0 4px 16px rgba(0,0,0,0.2);
}
.msg-tool {
    background: rgba(6,182,212,0.07);
    border: 1px solid rgba(6,182,212,0.2);
    border-left: 3px solid var(--accent-cyan);
    color: #67e8f9; padding: 8px 14px;
    border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
    font-family: 'Fira Code', monospace; font-size: 0.8125rem;
    margin: 4px 0;
}
.msg-timestamp {
    font-size: 0.7rem; color: var(--text-muted);
    margin-top: 2px; padding: 0 4px;
}
.msg-wrapper-user { display: flex; flex-direction: column; align-items: flex-end; margin: 6px 0; }
.msg-wrapper-assistant { display: flex; flex-direction: column; align-items: flex-start; margin: 6px 0; }

/* ── Sidebar brand ── */
.sidebar-brand {
    padding: 20px 16px 12px;
    border-bottom: 1px solid var(--border-glass);
    margin-bottom: 8px;
}
.sidebar-logo {
    font-size: 1.25rem; font-weight: 800;
    background: linear-gradient(135deg, #a5b4fc, #67e8f9);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    background-clip: text; letter-spacing: -0.02em;
}
.sidebar-tagline { font-size: 0.7rem; color: var(--text-muted); letter-spacing: 0.06em; margin-top: 2px; }

.sidebar-user {
    display: flex; align-items: center; gap: 10px;
    padding: 10px 14px; margin: 8px 0;
    background: var(--bg-glass); border-radius: var(--radius-md);
    border: 1px solid var(--border-glass);
}
.avatar {
    width: 34px; height: 34px; border-radius: 50%;
    background: linear-gradient(135deg, #6366f1, #06b6d4);
    display: flex; align-items: center; justify-content: center;
    font-weight: 700; font-size: 0.875rem; color: white;
    flex-shrink: 0;
}
.user-name { font-size: 0.8125rem; font-weight: 600; color: var(--text-primary); }
.user-role { font-size: 0.7rem; color: var(--text-muted); }

.sidebar-section-label {
    font-size: 0.65rem; font-weight: 700; color: var(--text-muted);
    text-transform: uppercase; letter-spacing: 0.1em;
    padding: 10px 16px 4px;
}

/* ── Pricing cards ── */
.price-card {
    background: var(--bg-glass);
    border: 1px solid var(--border-glass);
    border-radius: var(--radius-xl);
    padding: 2rem;
    backdrop-filter: blur(16px);
    box-shadow: var(--shadow-card);
    transition: var(--transition);
    position: relative; overflow: hidden;
    height: 100%;
}
.price-card::before {
    content: '';
    position: absolute; top: 0; left: 0; right: 0;
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.1), transparent);
}
.price-card:hover {
    transform: translateY(-6px);
    box-shadow: var(--shadow-3d);
}
.price-card.popular {
    border-color: rgba(99,102,241,0.5);
    box-shadow: 0 0 0 1px rgba(99,102,241,0.3), var(--shadow-3d);
}
.price-card.popular::before {
    background: linear-gradient(90deg, transparent, rgba(99,102,241,0.5), transparent);
}
.price-name { font-size: 0.8125rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; color: var(--text-muted); }
.price-amount { font-size: 3rem; font-weight: 800; color: var(--text-primary); letter-spacing: -0.03em; line-height: 1; margin: 0.5rem 0; }
.price-period { font-size: 0.875rem; color: var(--text-muted); }
.price-desc { font-size: 0.875rem; color: var(--text-secondary); margin: 1rem 0; }
.price-feature {
    display: flex; align-items: center; gap: 8px;
    font-size: 0.875rem; color: var(--text-secondary);
    padding: 6px 0;
}
.price-feature .check { color: var(--accent-green); font-size: 1rem; }
.popular-tag {
    position: absolute; top: 16px; right: 16px;
    background: linear-gradient(135deg, #6366f1, #4f46e5);
    color: white; font-size: 0.7rem; font-weight: 700;
    padding: 3px 10px; border-radius: 99px;
    letter-spacing: 0.05em; text-transform: uppercase;
    box-shadow: 0 2px 8px rgba(99,102,241,0.4);
}

/* ── Stat cards (admin) ── */
.stat-card {
    background: var(--bg-glass);
    border: 1px solid var(--border-glass);
    border-radius: var(--radius-lg);
    padding: 1.25rem 1.5rem;
    backdrop-filter: blur(12px);
    box-shadow: var(--shadow-card);
    transition: var(--transition);
    position: relative; overflow: hidden;
}
.stat-card::after {
    content: '';
    position: absolute; bottom: 0; left: 0; right: 0;
    height: 2px;
    border-radius: 0 0 var(--radius-lg) var(--radius-lg);
}
.stat-card.purple::after { background: linear-gradient(90deg, #6366f1, #818cf8); }
.stat-card.blue::after   { background: linear-gradient(90deg, #3b82f6, #60a5fa); }
.stat-card.green::after  { background: linear-gradient(90deg, #10b981, #34d399); }
.stat-card.orange::after { background: linear-gradient(90deg, #f59e0b, #fcd34d); }
.stat-card:hover { transform: translateY(-3px); box-shadow: var(--shadow-3d); }

.stat-icon {
    width: 40px; height: 40px; border-radius: var(--radius-md);
    display: flex; align-items: center; justify-content: center;
    font-size: 1.125rem; margin-bottom: 0.75rem;
}
.stat-icon.purple { background: rgba(99,102,241,0.15); }
.stat-icon.blue   { background: rgba(59,130,246,0.15); }
.stat-icon.green  { background: rgba(16,185,129,0.15); }
.stat-icon.orange { background: rgba(245,158,11,0.15); }

.stat-value { font-size: 2rem; font-weight: 800; color: var(--text-primary); letter-spacing: -0.03em; }
.stat-label { font-size: 0.8125rem; font-weight: 500; color: var(--text-muted); margin-top: 2px; text-transform: uppercase; letter-spacing: 0.06em; }
.stat-trend { font-size: 0.78rem; font-weight: 600; margin-top: 6px; }
.trend-up { color: var(--accent-green); }
.trend-down { color: var(--accent-red); }

/* ── Page header ── */
.page-header {
    padding: 0 0 1.5rem 0;
    border-bottom: 1px solid var(--border-glass);
    margin-bottom: 1.5rem;
}
.page-title {
    font-size: 1.75rem; font-weight: 800;
    color: var(--text-primary); letter-spacing: -0.03em;
    margin: 0;
}
.page-subtitle { font-size: 0.9rem; color: var(--text-muted); margin: 4px 0 0; }

/* ── Chat input override ── */
[data-testid="stChatInput"] {
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid var(--border-glass) !important;
    border-radius: var(--radius-xl) !important;
    backdrop-filter: blur(12px) !important;
}
[data-testid="stChatInput"]:focus-within {
    border-color: var(--accent-purple) !important;
    box-shadow: 0 0 0 3px rgba(99,102,241,0.15) !important;
}
[data-testid="stChatInput"] textarea {
    color: var(--text-primary) !important;
    font-family: 'Inter', sans-serif !important;
}

/* ── Chat message native ── */
[data-testid="stChatMessage"] {
    background: transparent !important;
    border: none !important;
    padding: 0.25rem 0 !important;
}

/* ── Forms ── */
[data-testid="stForm"] {
    background: transparent !important;
    border: none !important;
}
</style>
""", unsafe_allow_html=True)

from frontend.utils.session_state import init_session_state, is_authenticated

init_session_state()

if "theme" not in st.session_state:
    st.session_state.theme = "dark"

from frontend.components.auth_forms import render_login_page, render_register_page
from frontend.components.sidebar import render_sidebar

page = st.session_state.get("page", "login")

if not is_authenticated():
    if page == "register":
        render_register_page()
    else:
        render_login_page()
    st.stop()

render_sidebar()

page = st.session_state.get("page", "chat")

if page in ("chat", "history", "agent"):
    from frontend.pages.chat_page import render_chat_page
    render_chat_page(page)
elif page == "documents":
    from frontend.pages.documents_page import render_documents_page
    render_documents_page()
elif page == "usage":
    from frontend.pages.usage_page import render_usage_page
    render_usage_page()
elif page == "subscription":
    from frontend.pages.subscription_page import render_subscription_page
    render_subscription_page()
elif page == "settings":
    from frontend.pages.settings_page import render_settings_page
    render_settings_page()
elif page == "admin":
    from frontend.pages.admin_page import render_admin_page
    render_admin_page()
else:
    from frontend.pages.chat_page import render_chat_page
    render_chat_page("chat")
