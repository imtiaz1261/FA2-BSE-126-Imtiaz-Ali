"""
styles/theme.py
---------------
Global CSS injected via st.markdown(..., unsafe_allow_html=True).
Covers:
  - CSS custom properties for light & dark palettes
  - Layout resets (sidebar width, main padding, input bar)
  - Chat bubble styling (user / assistant)
  - Code block styling
  - Agent-progress panel
  - Skeleton loader animation
  - Smooth scrollbar
  - Responsive tweaks
"""

from __future__ import annotations


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_css(dark_mode: bool = False) -> str:
    """Return the full CSS string for the requested colour scheme."""
    palette = _DARK_PALETTE if dark_mode else _LIGHT_PALETTE
    return _BASE_CSS.format(**palette)


# ---------------------------------------------------------------------------
# Colour palettes
# ---------------------------------------------------------------------------

_LIGHT_PALETTE: dict[str, str] = {
    "bg_primary":     "#ffffff",
    "bg_secondary":   "#f7f7f8",
    "bg_sidebar":     "#202123",
    "bg_input":       "#ffffff",
    "bg_user_msg":    "#343541",
    "bg_ai_msg":      "#f7f7f8",
    "bg_card":        "#ffffff",
    "bg_card_hover":  "#f0f4ff",
    "bg_code":        "#1e1e2e",
    "border_color":   "#e5e7eb",
    "text_primary":   "#1a1a2e",
    "text_secondary": "#6b7280",
    "text_sidebar":   "#ececf1",
    "text_user_msg":  "#ffffff",
    "text_ai_msg":    "#1a1a2e",
    "text_code":      "#cdd6f4",
    "accent":         "#10a37f",
    "accent_hover":   "#0d8a6b",
    "accent_danger":  "#ef4444",
    "accent_warn":    "#f59e0b",
    "shadow":         "rgba(0,0,0,0.08)",
    "scrollbar_track":"#f1f1f1",
    "scrollbar_thumb":"#c1c1c1",
}

_DARK_PALETTE: dict[str, str] = {
    "bg_primary":     "#1a1a2e",
    "bg_secondary":   "#16213e",
    "bg_sidebar":     "#0f0f23",
    "bg_input":       "#2d2d44",
    "bg_user_msg":    "#2563eb",
    "bg_ai_msg":      "#16213e",
    "bg_card":        "#1e1e3a",
    "bg_card_hover":  "#252545",
    "bg_code":        "#0d0d1a",
    "border_color":   "#2d2d50",
    "text_primary":   "#e8e8f0",
    "text_secondary": "#8b8bab",
    "text_sidebar":   "#ececf1",
    "text_user_msg":  "#ffffff",
    "text_ai_msg":    "#e8e8f0",
    "text_code":      "#cdd6f4",
    "accent":         "#10a37f",
    "accent_hover":   "#0d8a6b",
    "accent_danger":  "#ef4444",
    "accent_warn":    "#f59e0b",
    "shadow":         "rgba(0,0,0,0.4)",
    "scrollbar_track":"#1a1a2e",
    "scrollbar_thumb":"#3d3d60",
}


# ---------------------------------------------------------------------------
# Base CSS template  (placeholders filled by get_css)
# ---------------------------------------------------------------------------

_BASE_CSS = """
<style>
/* ══════════════════════════════════════════════════
   1. RESET & ROOT VARIABLES
══════════════════════════════════════════════════ */
:root {{
    --bg-primary:      {bg_primary};
    --bg-secondary:    {bg_secondary};
    --bg-sidebar:      {bg_sidebar};
    --bg-input:        {bg_input};
    --bg-user-msg:     {bg_user_msg};
    --bg-ai-msg:       {bg_ai_msg};
    --bg-card:         {bg_card};
    --bg-card-hover:   {bg_card_hover};
    --bg-code:         {bg_code};
    --border-color:    {border_color};
    --text-primary:    {text_primary};
    --text-secondary:  {text_secondary};
    --text-sidebar:    {text_sidebar};
    --text-user-msg:   {text_user_msg};
    --text-ai-msg:     {text_ai_msg};
    --text-code:       {text_code};
    --accent:          {accent};
    --accent-hover:    {accent_hover};
    --accent-danger:   {accent_danger};
    --accent-warn:     {accent_warn};
    --shadow:          {shadow};
    --radius-sm:       6px;
    --radius-md:       12px;
    --radius-lg:       18px;
    --radius-xl:       24px;
    --font-sans:       'Inter', 'Segoe UI', system-ui, sans-serif;
    --font-mono:       'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace;
    --transition:      0.2s ease;
}}

/* ══════════════════════════════════════════════════
   2. GLOBAL OVERRIDES
══════════════════════════════════════════════════ */
html, body, [class*="css"] {{
    font-family: var(--font-sans) !important;
    background-color: var(--bg-primary) !important;
    color: var(--text-primary) !important;
}}

/* Hide default Streamlit chrome */
#MainMenu, footer, header {{ visibility: hidden; }}
.stDeployButton {{ display: none !important; }}

/* Remove default block padding */
.block-container {{
    padding: 0 !important;
    max-width: 100% !important;
}}

/* ══════════════════════════════════════════════════
   3. SIDEBAR
══════════════════════════════════════════════════ */
section[data-testid="stSidebar"] {{
    background-color: var(--bg-sidebar) !important;
    border-right: 1px solid rgba(255,255,255,0.05);
    min-width: 260px !important;
    max-width: 280px !important;
}}

section[data-testid="stSidebar"] * {{
    color: var(--text-sidebar) !important;
}}

section[data-testid="stSidebar"] .stButton > button {{
    width: 100%;
    background: transparent;
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: var(--radius-sm);
    color: var(--text-sidebar) !important;
    padding: 8px 12px;
    text-align: left;
    transition: background var(--transition);
    font-size: 0.875rem;
}}

section[data-testid="stSidebar"] .stButton > button:hover {{
    background: rgba(255,255,255,0.08) !important;
    border-color: rgba(255,255,255,0.2);
}}

.sidebar-new-chat-btn button {{
    background: var(--accent) !important;
    border: none !important;
    border-radius: var(--radius-sm) !important;
    color: #fff !important;
    font-weight: 600 !important;
    padding: 10px 16px !important;
    width: 100% !important;
    transition: background var(--transition) !important;
}}

.sidebar-new-chat-btn button:hover {{
    background: var(--accent-hover) !important;
}}

.sidebar-logo {{
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 16px 4px 8px;
    border-bottom: 1px solid rgba(255,255,255,0.08);
    margin-bottom: 12px;
}}

.sidebar-logo .logo-icon {{
    font-size: 1.8rem;
}}

.sidebar-logo .logo-title {{
    font-size: 1.1rem;
    font-weight: 700;
    letter-spacing: -0.3px;
    color: #fff !important;
}}

.sidebar-logo .logo-sub {{
    font-size: 0.7rem;
    color: rgba(255,255,255,0.45) !important;
    letter-spacing: 0.5px;
    text-transform: uppercase;
}}

.conv-item {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 7px 10px;
    border-radius: var(--radius-sm);
    cursor: pointer;
    transition: background var(--transition);
    margin-bottom: 2px;
}}

.conv-item:hover {{ background: rgba(255,255,255,0.06); }}
.conv-item.active {{ background: rgba(255,255,255,0.12); }}

.conv-item .conv-title {{
    font-size: 0.82rem;
    color: var(--text-sidebar) !important;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 160px;
}}

.conv-item .conv-time {{
    font-size: 0.68rem;
    color: rgba(255,255,255,0.35) !important;
}}

.sidebar-section-label {{
    font-size: 0.68rem;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    color: rgba(255,255,255,0.35) !important;
    padding: 10px 4px 4px;
    font-weight: 600;
}}

/* ══════════════════════════════════════════════════
   4. MAIN CONTENT AREA
══════════════════════════════════════════════════ */
.main-wrapper {{
    display: flex;
    flex-direction: column;
    height: 100vh;
    background: var(--bg-primary);
    overflow: hidden;
}}

.chat-container {{
    flex: 1;
    overflow-y: auto;
    padding: 24px 0 140px;
    scroll-behavior: smooth;
}}

/* ══════════════════════════════════════════════════
   5. CHAT MESSAGES
══════════════════════════════════════════════════ */
.message-row {{
    display: flex;
    align-items: flex-start;
    gap: 14px;
    padding: 10px 0;
    max-width: 860px;
    margin: 0 auto;
    padding-left: 16px;
    padding-right: 16px;
    animation: fadeSlideIn 0.25s ease;
}}

@keyframes fadeSlideIn {{
    from {{ opacity: 0; transform: translateY(8px); }}
    to   {{ opacity: 1; transform: translateY(0); }}
}}

.message-row.user {{ flex-direction: row-reverse; }}

.avatar {{
    width: 36px;
    height: 36px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1rem;
    flex-shrink: 0;
    font-weight: 700;
}}

.avatar.user-avatar {{
    background: var(--accent);
    color: #fff;
}}

.avatar.ai-avatar {{
    background: linear-gradient(135deg, #6366f1, #8b5cf6);
    color: #fff;
}}

.bubble {{
    max-width: 72%;
    padding: 12px 16px;
    border-radius: var(--radius-lg);
    line-height: 1.65;
    font-size: 0.925rem;
    box-shadow: 0 1px 4px var(--shadow);
    position: relative;
    word-break: break-word;
}}

.bubble.user-bubble {{
    background: var(--bg-user-msg);
    color: var(--text-user-msg);
    border-bottom-right-radius: var(--radius-sm);
}}

.bubble.ai-bubble {{
    background: var(--bg-ai-msg);
    color: var(--text-ai-msg);
    border-bottom-left-radius: var(--radius-sm);
    border: 1px solid var(--border-color);
}}

.message-meta {{
    display: flex;
    align-items: center;
    gap: 8px;
    margin-top: 6px;
    font-size: 0.72rem;
    color: var(--text-secondary);
    flex-wrap: wrap;
}}

.message-row.user .message-meta {{
    justify-content: flex-end;
}}

.action-btn {{
    background: none;
    border: 1px solid var(--border-color);
    border-radius: var(--radius-sm);
    padding: 3px 8px;
    font-size: 0.72rem;
    cursor: pointer;
    color: var(--text-secondary);
    transition: all var(--transition);
    display: inline-flex;
    align-items: center;
    gap: 4px;
}}

.action-btn:hover {{
    background: var(--bg-card-hover);
    border-color: var(--accent);
    color: var(--accent);
}}

/* ══════════════════════════════════════════════════
   6. CODE BLOCKS
══════════════════════════════════════════════════ */
.stCodeBlock, pre, code {{
    font-family: var(--font-mono) !important;
    font-size: 0.85rem !important;
}}

.stCodeBlock {{
    border-radius: var(--radius-md) !important;
    border: 1px solid var(--border-color) !important;
    position: relative;
}}

.code-header {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: #2d2d3e;
    border-radius: var(--radius-md) var(--radius-md) 0 0;
    padding: 6px 14px;
    font-size: 0.75rem;
    color: #a0a0b8;
    font-family: var(--font-mono);
}}

/* ══════════════════════════════════════════════════
   7. CHAT INPUT BAR
══════════════════════════════════════════════════ */
.input-bar-wrapper {{
    position: fixed;
    bottom: 0;
    left: 260px;         /* sidebar width */
    right: 0;
    background: linear-gradient(transparent, var(--bg-primary) 18%);
    padding: 12px 0 20px;
    z-index: 100;
}}

.input-bar {{
    max-width: 860px;
    margin: 0 auto;
    padding: 0 16px;
    display: flex;
    align-items: flex-end;
    gap: 10px;
    background: var(--bg-input);
    border: 1.5px solid var(--border-color);
    border-radius: var(--radius-xl);
    box-shadow: 0 4px 20px var(--shadow);
    padding: 10px 14px;
    transition: border-color var(--transition), box-shadow var(--transition);
}}

.input-bar:focus-within {{
    border-color: var(--accent);
    box-shadow: 0 4px 24px rgba(16,163,127,0.15);
}}

/* Streamlit textarea override */
.stChatInput textarea, .stTextArea textarea {{
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    font-size: 0.925rem !important;
    color: var(--text-primary) !important;
    resize: none !important;
    padding: 0 !important;
}}

.stChatInput {{
    background: var(--bg-input) !important;
    border: 1.5px solid var(--border-color) !important;
    border-radius: var(--radius-xl) !important;
    padding: 10px 16px !important;
}}

.stChatInput:focus-within {{
    border-color: var(--accent) !important;
    box-shadow: 0 4px 24px rgba(16,163,127,0.15) !important;
}}

/* ══════════════════════════════════════════════════
   8. AGENT PROGRESS PANEL
══════════════════════════════════════════════════ */
.agent-panel {{
    background: var(--bg-secondary);
    border: 1px solid var(--border-color);
    border-radius: var(--radius-md);
    padding: 14px 16px;
    margin: 0 auto 12px;
    max-width: 860px;
}}

.agent-panel-title {{
    font-size: 0.78rem;
    text-transform: uppercase;
    letter-spacing: 0.7px;
    color: var(--text-secondary);
    font-weight: 600;
    margin-bottom: 10px;
}}

.agent-step {{
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 7px 0;
    border-bottom: 1px solid var(--border-color);
    font-size: 0.875rem;
}}

.agent-step:last-child {{ border-bottom: none; }}

.agent-icon {{ font-size: 1rem; width: 22px; text-align: center; }}

.agent-name {{ font-weight: 600; color: var(--text-primary); }}

.agent-status {{
    font-size: 0.78rem;
    color: var(--text-secondary);
    margin-left: auto;
}}

.status-pill {{
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 2px 8px;
    border-radius: 20px;
    font-size: 0.72rem;
    font-weight: 600;
}}

.status-pill.idle    {{ background: rgba(107,114,128,0.12); color: #6b7280; }}
.status-pill.running {{ background: rgba(16,163,127,0.12); color: var(--accent); }}
.status-pill.done    {{ background: rgba(16,163,127,0.15); color: var(--accent); }}
.status-pill.error   {{ background: rgba(239,68,68,0.12); color: var(--accent-danger); }}

/* Pulsing dot */
.pulse {{
    width: 8px;
    height: 8px;
    background: var(--accent);
    border-radius: 50%;
    animation: pulse 1.4s ease-in-out infinite;
    display: inline-block;
}}

@keyframes pulse {{
    0%, 100% {{ opacity: 1; transform: scale(1); }}
    50%       {{ opacity: 0.4; transform: scale(0.8); }}
}}

/* ══════════════════════════════════════════════════
   9. EMPTY STATE / WELCOME SCREEN
══════════════════════════════════════════════════ */
.welcome-screen {{
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 60px 24px 160px;
    text-align: center;
    min-height: 70vh;
}}

.welcome-logo {{
    font-size: 3.5rem;
    margin-bottom: 12px;
    filter: drop-shadow(0 4px 16px rgba(16,163,127,0.3));
}}

.welcome-title {{
    font-size: 1.9rem;
    font-weight: 700;
    color: var(--text-primary);
    margin-bottom: 8px;
    letter-spacing: -0.5px;
}}

.welcome-subtitle {{
    font-size: 1rem;
    color: var(--text-secondary);
    max-width: 480px;
    line-height: 1.6;
    margin-bottom: 36px;
}}

.prompt-cards-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 12px;
    max-width: 760px;
    width: 100%;
}}

.prompt-card {{
    background: var(--bg-card);
    border: 1.5px solid var(--border-color);
    border-radius: var(--radius-md);
    padding: 14px 16px;
    cursor: pointer;
    transition: all var(--transition);
    text-align: left;
}}

.prompt-card:hover {{
    background: var(--bg-card-hover);
    border-color: var(--accent);
    transform: translateY(-2px);
    box-shadow: 0 4px 16px var(--shadow);
}}

.prompt-card .card-icon {{ font-size: 1.3rem; margin-bottom: 6px; }}

.prompt-card .card-title {{
    font-size: 0.875rem;
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: 4px;
}}

.prompt-card .card-desc {{
    font-size: 0.77rem;
    color: var(--text-secondary);
    line-height: 1.4;
}}

/* ══════════════════════════════════════════════════
   10. INFO PANEL (right side)
══════════════════════════════════════════════════ */
.info-panel {{
    background: var(--bg-secondary);
    border: 1px solid var(--border-color);
    border-radius: var(--radius-md);
    padding: 16px;
    font-size: 0.85rem;
}}

.info-row {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 6px 0;
    border-bottom: 1px solid var(--border-color);
    font-size: 0.82rem;
}}

.info-row:last-child {{ border-bottom: none; }}
.info-label {{ color: var(--text-secondary); }}
.info-value {{ font-weight: 600; color: var(--text-primary); }}

/* ══════════════════════════════════════════════════
   11. SKELETON LOADER
══════════════════════════════════════════════════ */
.skeleton {{
    background: linear-gradient(
        90deg,
        var(--border-color) 25%,
        var(--bg-secondary) 50%,
        var(--border-color) 75%
    );
    background-size: 200% 100%;
    animation: shimmer 1.5s infinite;
    border-radius: var(--radius-sm);
    height: 16px;
    margin-bottom: 8px;
}}

@keyframes shimmer {{
    from {{ background-position: 200% 0; }}
    to   {{ background-position: -200% 0; }}
}}

.skeleton.short {{ width: 45%; }}
.skeleton.medium {{ width: 72%; }}
.skeleton.long  {{ width: 90%; }}

/* ══════════════════════════════════════════════════
   12. TYPING INDICATOR
══════════════════════════════════════════════════ */
.typing-indicator {{
    display: flex;
    align-items: center;
    gap: 5px;
    padding: 10px 14px;
    background: var(--bg-ai-msg);
    border: 1px solid var(--border-color);
    border-radius: var(--radius-lg);
    border-bottom-left-radius: var(--radius-sm);
    width: fit-content;
}}

.typing-dot {{
    width: 8px;
    height: 8px;
    background: var(--text-secondary);
    border-radius: 50%;
    animation: typing-bounce 1.4s ease-in-out infinite;
}}

.typing-dot:nth-child(1) {{ animation-delay: 0s; }}
.typing-dot:nth-child(2) {{ animation-delay: 0.2s; }}
.typing-dot:nth-child(3) {{ animation-delay: 0.4s; }}

@keyframes typing-bounce {{
    0%, 60%, 100% {{ transform: translateY(0); opacity: 0.4; }}
    30%           {{ transform: translateY(-6px); opacity: 1; }}
}}

/* ══════════════════════════════════════════════════
   13. NOTIFICATION TOAST
══════════════════════════════════════════════════ */
.toast {{
    position: fixed;
    bottom: 90px;
    right: 24px;
    padding: 10px 18px;
    border-radius: var(--radius-md);
    font-size: 0.875rem;
    font-weight: 500;
    z-index: 9999;
    box-shadow: 0 4px 20px var(--shadow);
    animation: slideInRight 0.3s ease;
}}

.toast.success {{ background: var(--accent); color: #fff; }}
.toast.error   {{ background: var(--accent-danger); color: #fff; }}
.toast.warn    {{ background: var(--accent-warn); color: #fff; }}

@keyframes slideInRight {{
    from {{ opacity: 0; transform: translateX(20px); }}
    to   {{ opacity: 1; transform: translateX(0); }}
}}

/* ══════════════════════════════════════════════════
   14. GENERAL STREAMLIT BUTTON OVERRIDES
══════════════════════════════════════════════════ */
.stButton > button {{
    border-radius: var(--radius-sm) !important;
    font-size: 0.875rem !important;
    transition: all var(--transition) !important;
}}

.primary-btn button {{
    background: var(--accent) !important;
    color: #fff !important;
    border: none !important;
    font-weight: 600 !important;
}}

.primary-btn button:hover {{
    background: var(--accent-hover) !important;
}}

.danger-btn button {{
    background: transparent !important;
    color: var(--accent-danger) !important;
    border: 1px solid var(--accent-danger) !important;
}}

.danger-btn button:hover {{
    background: rgba(239,68,68,0.08) !important;
}}

/* ══════════════════════════════════════════════════
   15. SCROLLBAR
══════════════════════════════════════════════════ */
::-webkit-scrollbar {{ width: 6px; height: 6px; }}
::-webkit-scrollbar-track {{ background: {scrollbar_track}; }}
::-webkit-scrollbar-thumb {{
    background: {scrollbar_thumb};
    border-radius: 3px;
}}
::-webkit-scrollbar-thumb:hover {{ background: var(--accent); }}

/* ══════════════════════════════════════════════════
   16. RESPONSIVE
══════════════════════════════════════════════════ */
@media (max-width: 768px) {{
    .bubble {{ max-width: 90%; }}
    .input-bar-wrapper {{ left: 0; }}
    .welcome-title {{ font-size: 1.4rem; }}
    .prompt-cards-grid {{ grid-template-columns: 1fr 1fr; }}
}}

@media (max-width: 480px) {{
    .prompt-cards-grid {{ grid-template-columns: 1fr; }}
}}

/* ══════════════════════════════════════════════════
   17. MISC UTILITIES
══════════════════════════════════════════════════ */
.divider {{
    height: 1px;
    background: var(--border-color);
    margin: 8px 0;
}}

.badge {{
    display: inline-flex;
    align-items: center;
    padding: 2px 8px;
    background: rgba(16,163,127,0.12);
    color: var(--accent);
    border-radius: 20px;
    font-size: 0.72rem;
    font-weight: 600;
}}

.section-header {{
    font-size: 1.1rem;
    font-weight: 700;
    color: var(--text-primary);
    margin-bottom: 12px;
    padding-bottom: 8px;
    border-bottom: 1px solid var(--border-color);
}}
</style>
"""
