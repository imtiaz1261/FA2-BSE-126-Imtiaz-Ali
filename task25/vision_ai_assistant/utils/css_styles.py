"""
utils/css_styles.py
===================
All custom CSS for the Vision AI Assistant premium dark theme.
Injected once via st.markdown(..., unsafe_allow_html=True) in app.py.

Design inspiration: ChatGPT's clean dark interface, with indigo accents.
"""

from __future__ import annotations

from config.constants import THEME

# ---------------------------------------------------------------------------
# Main CSS block
# ---------------------------------------------------------------------------

def get_main_css() -> str:
    """Return the full custom CSS string for injection."""
    t = THEME
    return f"""
<style>
/* ============================================================
   GLOBAL RESET & BASE
   ============================================================ */
* {{ box-sizing: border-box; }}

html, body, [data-testid="stAppViewContainer"] {{
    background-color: {t['background']} !important;
    color: {t['text_primary']} !important;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI',
                 Roboto, Oxygen, sans-serif !important;
}}

/* Hide Streamlit default header/footer decorations */
#MainMenu {{ visibility: hidden; }}
footer {{ visibility: hidden; }}
[data-testid="stHeader"] {{ background: transparent; }}
[data-testid="stDecoration"] {{ display: none; }}
[data-testid="stToolbar"] {{ display: none; }}

/* ============================================================
   SIDEBAR
   ============================================================ */
[data-testid="stSidebar"] {{
    background: {t['surface']} !important;
    border-right: 1px solid {t['border']} !important;
    padding: 0 !important;
}}

[data-testid="stSidebar"] > div:first-child {{
    padding: 1rem 0.75rem;
}}

/* Sidebar text */
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] .stMarkdown p,
[data-testid="stSidebar"] span {{
    color: {t['text_secondary']} !important;
    font-size: 0.875rem !important;
}}

/* ============================================================
   MAIN CONTENT AREA
   ============================================================ */
.main .block-container {{
    padding: 1rem 1.5rem !important;
    max-width: 100% !important;
}}

/* ============================================================
   BUTTONS
   ============================================================ */
.stButton > button {{
    background: {t['primary']} !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 500 !important;
    padding: 0.5rem 1.25rem !important;
    transition: background 0.2s ease, transform 0.1s ease !important;
    cursor: pointer !important;
}}

.stButton > button:hover {{
    background: {t['primary_hover']} !important;
    transform: translateY(-1px) !important;
}}

.stButton > button:active {{
    transform: translateY(0) !important;
}}

/* Secondary button style — wrap in a div.secondary-btn */
.secondary-btn .stButton > button {{
    background: transparent !important;
    border: 1px solid {t['border']} !important;
    color: {t['text_secondary']} !important;
}}

.secondary-btn .stButton > button:hover {{
    border-color: {t['primary']} !important;
    color: {t['primary']} !important;
}}

/* ============================================================
   TEXT INPUTS & TEXT AREA
   ============================================================ */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea {{
    background: {t['surface_2']} !important;
    border: 1px solid {t['border']} !important;
    border-radius: 10px !important;
    color: {t['text_primary']} !important;
    font-size: 0.95rem !important;
    padding: 0.6rem 1rem !important;
    transition: border-color 0.2s ease !important;
}}

.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {{
    border-color: {t['primary']} !important;
    outline: none !important;
    box-shadow: 0 0 0 3px {t['primary']}33 !important;
}}

/* Chat input specific */
[data-testid="stChatInput"] > div {{
    background: {t['surface_2']} !important;
    border: 1px solid {t['border']} !important;
    border-radius: 12px !important;
}}

[data-testid="stChatInput"] textarea {{
    background: transparent !important;
    color: {t['text_primary']} !important;
}}

/* ============================================================
   SELECTBOX / DROPDOWN
   ============================================================ */
.stSelectbox > div > div {{
    background: {t['surface_2']} !important;
    border: 1px solid {t['border']} !important;
    border-radius: 8px !important;
    color: {t['text_primary']} !important;
}}

/* ============================================================
   FILE UPLOADER
   ============================================================ */
[data-testid="stFileUploader"] {{
    background: {t['surface']} !important;
    border: 2px dashed {t['border']} !important;
    border-radius: 12px !important;
    padding: 1rem !important;
    transition: border-color 0.2s ease !important;
}}

[data-testid="stFileUploader"]:hover {{
    border-color: {t['primary']} !important;
}}

[data-testid="stFileUploader"] label {{
    color: {t['text_secondary']} !important;
}}

/* ============================================================
   CHAT MESSAGES
   ============================================================ */
.chat-message {{
    display: flex;
    gap: 12px;
    padding: 1rem 0.5rem;
    border-radius: 12px;
    margin-bottom: 0.5rem;
    animation: fadeInUp 0.3s ease;
}}

.chat-message.user {{
    background: {t['user_bubble']};
    flex-direction: row-reverse;
}}

.chat-message.assistant {{
    background: {t['ai_bubble']};
}}

.chat-avatar {{
    width: 36px;
    height: 36px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1rem;
    flex-shrink: 0;
    font-weight: bold;
}}

.chat-avatar.user-avatar {{
    background: {t['primary']};
    color: white;
}}

.chat-avatar.ai-avatar {{
    background: {t['secondary']};
    color: white;
}}

.chat-content {{
    flex: 1;
    min-width: 0;
}}

.chat-meta {{
    font-size: 0.72rem;
    color: {t['text_muted']};
    margin-bottom: 4px;
}}

.chat-text {{
    color: {t['text_primary']};
    line-height: 1.6;
    font-size: 0.93rem;
}}

/* ============================================================
   CODE BLOCKS
   ============================================================ */
pre, code {{
    background: {t['code_bg']} !important;
    border: 1px solid {t['border']} !important;
    border-radius: 8px !important;
    font-family: 'JetBrains Mono', 'Fira Code', 'Cascadia Code',
                 Consolas, monospace !important;
    font-size: 0.82rem !important;
}}

pre {{
    padding: 1rem !important;
    overflow-x: auto !important;
}}

code {{
    padding: 2px 6px !important;
    font-size: 0.85em !important;
}}

/* ============================================================
   CARDS (prompt cards, info cards)
   ============================================================ */
.prompt-card {{
    background: {t['surface']};
    border: 1px solid {t['border']};
    border-radius: 12px;
    padding: 1rem 1.2rem;
    cursor: pointer;
    transition: border-color 0.2s ease, transform 0.15s ease,
                box-shadow 0.2s ease;
    text-align: left;
}}

.prompt-card:hover {{
    border-color: {t['primary']};
    transform: translateY(-2px);
    box-shadow: 0 4px 20px {t['primary']}22;
}}

.prompt-card .card-icon {{
    font-size: 1.5rem;
    margin-bottom: 6px;
}}

.prompt-card .card-title {{
    font-weight: 600;
    font-size: 0.88rem;
    color: {t['text_primary']};
    margin-bottom: 4px;
}}

.prompt-card .card-prompt {{
    font-size: 0.78rem;
    color: {t['text_muted']};
    line-height: 1.4;
}}

/* ============================================================
   IMAGE VIEWER PANEL
   ============================================================ */
.image-panel {{
    background: {t['surface']};
    border: 1px solid {t['border']};
    border-radius: 16px;
    padding: 1rem;
    height: 100%;
}}

.image-panel img {{
    width: 100%;
    border-radius: 10px;
    object-fit: contain;
    max-height: 480px;
}}

.image-info-row {{
    display: flex;
    justify-content: space-between;
    font-size: 0.78rem;
    color: {t['text_muted']};
    margin-top: 8px;
    padding-top: 8px;
    border-top: 1px solid {t['border']};
}}

/* ============================================================
   METRICS / INFO BOXES
   ============================================================ */
[data-testid="stMetric"] {{
    background: {t['surface']} !important;
    border: 1px solid {t['border']} !important;
    border-radius: 10px !important;
    padding: 0.75rem !important;
}}

[data-testid="stMetricLabel"] {{
    color: {t['text_muted']} !important;
    font-size: 0.78rem !important;
}}

[data-testid="stMetricValue"] {{
    color: {t['text_primary']} !important;
    font-size: 1.4rem !important;
}}

/* ============================================================
   EXPANDERS
   ============================================================ */
[data-testid="stExpander"] {{
    background: {t['surface']} !important;
    border: 1px solid {t['border']} !important;
    border-radius: 10px !important;
}}

[data-testid="stExpander"] summary {{
    color: {t['text_secondary']} !important;
    font-weight: 500 !important;
}}

/* ============================================================
   DIVIDERS
   ============================================================ */
hr {{
    border-color: {t['border']} !important;
    margin: 1rem 0 !important;
}}

/* ============================================================
   SCROLLBAR
   ============================================================ */
::-webkit-scrollbar {{
    width: 6px;
    height: 6px;
}}

::-webkit-scrollbar-track {{
    background: {t['background']};
}}

::-webkit-scrollbar-thumb {{
    background: {t['border']};
    border-radius: 3px;
}}

::-webkit-scrollbar-thumb:hover {{
    background: {t['text_muted']};
}}

/* ============================================================
   ANIMATIONS
   ============================================================ */
@keyframes fadeInUp {{
    from {{ opacity: 0; transform: translateY(8px); }}
    to   {{ opacity: 1; transform: translateY(0); }}
}}

@keyframes pulse {{
    0%, 100% {{ opacity: 1; }}
    50%       {{ opacity: 0.5; }}
}}

.typing-indicator {{
    display: inline-block;
    animation: pulse 1s ease-in-out infinite;
    color: {t['primary']};
    font-size: 1.2rem;
    letter-spacing: 2px;
}}

/* ============================================================
   SIDEBAR NAV ITEMS
   ============================================================ */
.sidebar-nav-item {{
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 12px;
    border-radius: 8px;
    cursor: pointer;
    color: {t['text_secondary']};
    font-size: 0.875rem;
    transition: background 0.15s ease, color 0.15s ease;
    margin-bottom: 2px;
}}

.sidebar-nav-item:hover {{
    background: {t['surface_2']};
    color: {t['text_primary']};
}}

.sidebar-nav-item.active {{
    background: {t['primary']}22;
    color: {t['primary']};
    font-weight: 500;
}}

/* ============================================================
   HISTORY LIST
   ============================================================ */
.history-item {{
    padding: 8px 10px;
    border-radius: 8px;
    cursor: pointer;
    transition: background 0.15s ease;
    border: 1px solid transparent;
    margin-bottom: 4px;
}}

.history-item:hover {{
    background: {t['surface_2']};
    border-color: {t['border']};
}}

.history-item .history-title {{
    font-size: 0.82rem;
    color: {t['text_primary']};
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}}

.history-item .history-meta {{
    font-size: 0.7rem;
    color: {t['text_muted']};
    margin-top: 2px;
}}

/* ============================================================
   WELCOME / EMPTY STATE
   ============================================================ */
.welcome-container {{
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 3rem 2rem;
    text-align: center;
    min-height: 300px;
}}

.welcome-logo {{
    font-size: 4rem;
    margin-bottom: 1rem;
}}

.welcome-title {{
    font-size: 1.6rem;
    font-weight: 700;
    color: {t['text_primary']};
    margin-bottom: 0.5rem;
}}

.welcome-subtitle {{
    font-size: 1rem;
    color: {t['text_secondary']};
    max-width: 480px;
    line-height: 1.6;
}}

/* ============================================================
   ALERT / STATUS BANNERS
   ============================================================ */
.status-banner {{
    padding: 0.75rem 1rem;
    border-radius: 8px;
    font-size: 0.875rem;
    margin-bottom: 0.75rem;
    display: flex;
    align-items: center;
    gap: 8px;
}}

.status-banner.warning {{
    background: {t['warning']}18;
    border: 1px solid {t['warning']}44;
    color: {t['warning']};
}}

.status-banner.error {{
    background: {t['error']}18;
    border: 1px solid {t['error']}44;
    color: {t['error']};
}}

.status-banner.success {{
    background: {t['success']}18;
    border: 1px solid {t['success']}44;
    color: {t['success']};
}}

.status-banner.info {{
    background: {t['primary']}18;
    border: 1px solid {t['primary']}44;
    color: {t['primary']};
}}

/* ============================================================
   TABS
   ============================================================ */
[data-testid="stTabs"] [data-baseweb="tab-list"] {{
    background: {t['surface']} !important;
    border-radius: 10px !important;
    padding: 4px !important;
    gap: 4px !important;
    border-bottom: none !important;
}}

[data-testid="stTabs"] [data-baseweb="tab"] {{
    background: transparent !important;
    border-radius: 7px !important;
    color: {t['text_secondary']} !important;
    padding: 6px 16px !important;
    font-size: 0.875rem !important;
    border: none !important;
}}

[data-testid="stTabs"] [aria-selected="true"] {{
    background: {t['primary']} !important;
    color: white !important;
}}

/* ============================================================
   TOOLTIPS (hover text)
   ============================================================ */
[title] {{
    cursor: help;
    text-decoration: underline dotted {t['text_muted']};
    text-underline-offset: 2px;
}}

/* ============================================================
   LOGO / BRANDING
   ============================================================ */
.app-logo {{
    font-size: 2rem;
    font-weight: 800;
    background: linear-gradient(135deg, {t['primary']}, {t['secondary']});
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    letter-spacing: -0.5px;
}}

.app-tagline {{
    font-size: 0.75rem;
    color: {t['text_muted']};
    letter-spacing: 0.5px;
}}

/* ============================================================
   BADGE UTILITIES
   ============================================================ */
.badge {{
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 500;
    white-space: nowrap;
}}

.badge-primary {{
    background: {t['primary']}22;
    color: {t['primary']};
    border: 1px solid {t['primary']}44;
}}

.badge-success {{
    background: {t['success']}22;
    color: {t['success']};
    border: 1px solid {t['success']}44;
}}

.badge-warning {{
    background: {t['warning']}22;
    color: {t['warning']};
    border: 1px solid {t['warning']}44;
}}

/* ============================================================
   COPY BUTTON (appears inside AI messages)
   ============================================================ */
.copy-btn {{
    background: transparent;
    border: 1px solid {t['border']};
    color: {t['text_muted']};
    border-radius: 6px;
    padding: 3px 8px;
    font-size: 0.72rem;
    cursor: pointer;
    transition: all 0.15s ease;
}}

.copy-btn:hover {{
    border-color: {t['primary']};
    color: {t['primary']};
}}
</style>
"""


def get_loading_css() -> str:
    """CSS for the streaming/loading animation."""
    return """
<style>
.streaming-dot {
    display: inline-block;
    width: 6px; height: 6px;
    border-radius: 50%;
    background: #6366f1;
    margin: 0 2px;
    animation: bounce 1.2s ease-in-out infinite;
}
.streaming-dot:nth-child(1) { animation-delay: 0s; }
.streaming-dot:nth-child(2) { animation-delay: 0.2s; }
.streaming-dot:nth-child(3) { animation-delay: 0.4s; }
@keyframes bounce {
    0%, 80%, 100% { transform: scale(0.8); opacity: 0.5; }
    40% { transform: scale(1.2); opacity: 1; }
}
</style>
"""
