"""
styles/theme.py
---------------
Centralised CSS for the Multi-Agent Research Assistant UI.

Two complete colour palettes (light / dark) are defined as Python
dicts so every component can read a single source of truth.
`apply_theme()` injects the compiled <style> block into the running
Streamlit page.  Call it once at the top of app.py.
"""

from __future__ import annotations

import streamlit as st

# ── Colour palettes ──────────────────────────────────────────────────────────

LIGHT: dict[str, str] = {
    "bg_primary":       "#FFFFFF",
    "bg_secondary":     "#F7F7F8",
    "bg_sidebar":       "#F0F0F0",
    "bg_input":         "#FFFFFF",
    "bg_user_bubble":   "#DCF8C6",
    "bg_ai_bubble":     "#F0F4FF",
    "bg_card":          "#FFFFFF",
    "bg_code":          "#1E1E2E",
    "border":           "#E5E7EB",
    "text_primary":     "#0D0D0D",
    "text_secondary":   "#6B7280",
    "text_muted":       "#9CA3AF",
    "text_code":        "#E2E8F0",
    "accent":           "#10A37F",        # ChatGPT green
    "accent_hover":     "#0D8F6E",
    "accent_light":     "#D1FAE5",
    "danger":           "#EF4444",
    "warning":          "#F59E0B",
    "success":          "#10B981",
    "info":             "#3B82F6",
    "shadow":           "rgba(0,0,0,0.08)",
    "scrollbar":        "#D1D5DB",
}

DARK: dict[str, str] = {
    "bg_primary":       "#212121",
    "bg_secondary":     "#2D2D2D",
    "bg_sidebar":       "#171717",
    "bg_input":         "#2D2D2D",
    "bg_user_bubble":   "#2A3F2E",
    "bg_ai_bubble":     "#1E2A3A",
    "bg_card":          "#2D2D2D",
    "bg_code":          "#0D1117",
    "border":           "#3F3F3F",
    "text_primary":     "#ECECEC",
    "text_secondary":   "#A1A1AA",
    "text_muted":       "#71717A",
    "text_code":        "#E2E8F0",
    "accent":           "#10A37F",
    "accent_hover":     "#0FCF9E",
    "accent_light":     "#1A3A2E",
    "danger":           "#F87171",
    "warning":          "#FCD34D",
    "success":          "#34D399",
    "info":             "#60A5FA",
    "shadow":           "rgba(0,0,0,0.40)",
    "scrollbar":        "#4B5563",
}


def get_palette(dark_mode: bool = False) -> dict[str, str]:
    """Return the active colour palette."""
    return DARK if dark_mode else LIGHT


def build_css(c: dict[str, str]) -> str:
    """
    Compile a full CSS string from the palette dict *c*.

    Covers:
    - Streamlit shell resets (header, toolbar, footer)
    - Layout & sidebar
    - Chat bubbles
    - Code blocks with syntax colours
    - Input bar
    - Buttons
    - Cards / agent status panel
    - Scrollbars
    - Animations (typing indicator, fade-in, skeleton)
    - Responsive breakpoints
    """
    return f"""
    /* ── Reset & base ─────────────────────────────────────────── */
    html, body, [data-testid="stAppViewContainer"] {{
        background-color: {c['bg_primary']} !important;
        color: {c['text_primary']} !important;
        font-family: 'Inter', 'Segoe UI', system-ui, -apple-system, sans-serif;
        font-size: 15px;
        line-height: 1.65;
    }}

    /* Hide Streamlit chrome */
    #MainMenu, footer, [data-testid="stToolbar"] {{
        visibility: hidden;
        height: 0;
    }}
    header[data-testid="stHeader"] {{
        background: transparent !important;
        height: 0 !important;
    }}

    /* ── Sidebar ───────────────────────────────────────────────── */
    [data-testid="stSidebar"] {{
        background-color: {c['bg_sidebar']} !important;
        border-right: 1px solid {c['border']} !important;
        padding: 0 !important;
    }}
    [data-testid="stSidebar"] > div:first-child {{
        padding: 1rem 0.75rem !important;
    }}
    [data-testid="stSidebarNav"] {{
        display: none;
    }}

    /* ── Main content area ────────────────────────────────────── */
    .main .block-container {{
        padding: 0 !important;
        max-width: 100% !important;
    }}

    /* ── Chat container ───────────────────────────────────────── */
    .chat-container {{
        display: flex;
        flex-direction: column;
        height: calc(100vh - 140px);
        overflow-y: auto;
        padding: 1.5rem 1rem 1rem;
        scroll-behavior: smooth;
    }}
    .chat-container::-webkit-scrollbar {{
        width: 6px;
    }}
    .chat-container::-webkit-scrollbar-track {{
        background: transparent;
    }}
    .chat-container::-webkit-scrollbar-thumb {{
        background: {c['scrollbar']};
        border-radius: 3px;
    }}

    /* ── Chat bubbles ─────────────────────────────────────────── */
    .message-row {{
        display: flex;
        gap: 0.75rem;
        margin-bottom: 1.25rem;
        animation: fadeIn 0.25s ease-in-out;
    }}
    .message-row.user {{
        flex-direction: row-reverse;
    }}
    .avatar {{
        width: 36px;
        height: 36px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 16px;
        flex-shrink: 0;
        font-weight: 600;
    }}
    .avatar.user {{
        background: {c['accent']};
        color: #fff;
    }}
    .avatar.ai {{
        background: {c['bg_ai_bubble']};
        border: 1px solid {c['border']};
        color: {c['accent']};
    }}
    .bubble {{
        max-width: 72%;
        padding: 0.75rem 1rem;
        border-radius: 18px;
        box-shadow: 0 1px 3px {c['shadow']};
        position: relative;
        word-break: break-word;
    }}
    .bubble.user {{
        background: {c['bg_user_bubble']};
        color: {c['text_primary']};
        border-bottom-right-radius: 4px;
    }}
    .bubble.ai {{
        background: {c['bg_ai_bubble']};
        color: {c['text_primary']};
        border-bottom-left-radius: 4px;
        border: 1px solid {c['border']};
    }}
    .bubble-meta {{
        font-size: 11px;
        color: {c['text_muted']};
        margin-top: 0.35rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }}
    .message-row.user .bubble-meta {{
        justify-content: flex-end;
    }}

    /* ── Code blocks ──────────────────────────────────────────── */
    .bubble pre, .bubble code {{
        background: {c['bg_code']} !important;
        color: {c['text_code']} !important;
        border-radius: 8px;
        font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
        font-size: 13px;
    }}
    .bubble pre {{
        padding: 1rem;
        overflow-x: auto;
        margin: 0.5rem 0;
        position: relative;
    }}
    .copy-btn {{
        position: absolute;
        top: 0.5rem;
        right: 0.5rem;
        background: {c['border']};
        color: {c['text_secondary']};
        border: none;
        border-radius: 5px;
        padding: 2px 8px;
        font-size: 11px;
        cursor: pointer;
        opacity: 0;
        transition: opacity 0.2s;
    }}
    .bubble pre:hover .copy-btn {{
        opacity: 1;
    }}

    /* ── Input bar ────────────────────────────────────────────── */
    .input-bar-wrapper {{
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        background: {c['bg_primary']};
        border-top: 1px solid {c['border']};
        padding: 0.75rem 1rem;
        z-index: 100;
    }}
    .input-inner {{
        max-width: 860px;
        margin: 0 auto;
        display: flex;
        gap: 0.5rem;
        align-items: flex-end;
    }}
    [data-testid="stTextArea"] textarea {{
        background: {c['bg_input']} !important;
        color: {c['text_primary']} !important;
        border: 1px solid {c['border']} !important;
        border-radius: 12px !important;
        padding: 0.75rem 1rem !important;
        font-size: 15px !important;
        resize: none !important;
        box-shadow: 0 0 0 0px {c['accent']} !important;
        transition: border-color 0.2s, box-shadow 0.2s !important;
    }}
    [data-testid="stTextArea"] textarea:focus {{
        border-color: {c['accent']} !important;
        box-shadow: 0 0 0 3px {c['accent_light']} !important;
    }}

    /* ── Primary / accent button ──────────────────────────────── */
    .stButton > button[kind="primary"],
    button.send-btn {{
        background: {c['accent']} !important;
        color: #fff !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 0.5rem 1.25rem !important;
        font-weight: 600 !important;
        font-size: 14px !important;
        transition: background 0.2s, transform 0.1s !important;
    }}
    .stButton > button[kind="primary"]:hover {{
        background: {c['accent_hover']} !important;
        transform: translateY(-1px);
    }}

    /* Secondary buttons */
    .stButton > button {{
        border-radius: 8px !important;
        font-size: 13px !important;
        transition: background 0.15s !important;
    }}

    /* ── Suggestion cards ─────────────────────────────────────── */
    .suggestion-card {{
        background: {c['bg_card']};
        border: 1px solid {c['border']};
        border-radius: 12px;
        padding: 0.85rem 1rem;
        cursor: pointer;
        transition: border-color 0.2s, box-shadow 0.2s, transform 0.15s;
        font-size: 14px;
        color: {c['text_secondary']};
        text-align: left;
    }}
    .suggestion-card:hover {{
        border-color: {c['accent']};
        box-shadow: 0 2px 8px {c['shadow']};
        transform: translateY(-2px);
        color: {c['text_primary']};
    }}

    /* ── Agent status panel ───────────────────────────────────── */
    .agent-panel {{
        background: {c['bg_secondary']};
        border: 1px solid {c['border']};
        border-radius: 12px;
        padding: 1rem;
        margin-bottom: 1rem;
    }}
    .agent-row {{
        display: flex;
        align-items: center;
        gap: 0.65rem;
        padding: 0.5rem 0;
        font-size: 14px;
        border-bottom: 1px solid {c['border']};
        transition: background 0.15s;
    }}
    .agent-row:last-child {{
        border-bottom: none;
    }}
    .agent-status-dot {{
        width: 10px;
        height: 10px;
        border-radius: 50%;
        flex-shrink: 0;
    }}
    .dot-idle     {{ background: {c['text_muted']}; }}
    .dot-running  {{ background: {c['warning']}; animation: pulse 1s infinite; }}
    .dot-done     {{ background: {c['success']}; }}
    .dot-error    {{ background: {c['danger']}; }}

    /* ── Info / right panel ───────────────────────────────────── */
    .info-panel {{
        background: {c['bg_secondary']};
        border: 1px solid {c['border']};
        border-radius: 12px;
        padding: 1rem;
        font-size: 13px;
        color: {c['text_secondary']};
    }}
    .info-panel h4 {{
        color: {c['text_primary']};
        font-size: 13px;
        font-weight: 600;
        margin: 0 0 0.5rem;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }}
    .info-row {{
        display: flex;
        justify-content: space-between;
        padding: 0.25rem 0;
        border-bottom: 1px solid {c['border']};
    }}
    .info-row:last-child {{ border-bottom: none; }}
    .info-value {{
        color: {c['text_primary']};
        font-weight: 500;
    }}

    /* ── Skeleton loader ──────────────────────────────────────── */
    .skeleton {{
        background: linear-gradient(
            90deg,
            {c['bg_secondary']} 25%,
            {c['border']} 50%,
            {c['bg_secondary']} 75%
        );
        background-size: 200% 100%;
        border-radius: 6px;
        animation: shimmer 1.4s infinite;
    }}
    .skeleton-line {{
        height: 14px;
        margin: 8px 0;
        border-radius: 4px;
    }}
    .skeleton-line.short  {{ width: 45%; }}
    .skeleton-line.medium {{ width: 70%; }}
    .skeleton-line.long   {{ width: 90%; }}

    /* ── Typing indicator ─────────────────────────────────────── */
    .typing-indicator {{
        display: flex;
        align-items: center;
        gap: 5px;
        padding: 0.75rem 1rem;
    }}
    .typing-dot {{
        width: 8px;
        height: 8px;
        background: {c['text_muted']};
        border-radius: 50%;
        animation: bounce 1.2s infinite;
    }}
    .typing-dot:nth-child(2) {{ animation-delay: 0.2s; }}
    .typing-dot:nth-child(3) {{ animation-delay: 0.4s; }}

    /* ── Notification toast ───────────────────────────────────── */
    .toast {{
        position: fixed;
        bottom: 100px;
        right: 1.5rem;
        background: {c['bg_card']};
        border: 1px solid {c['border']};
        border-radius: 10px;
        padding: 0.75rem 1.25rem;
        box-shadow: 0 4px 16px {c['shadow']};
        z-index: 9999;
        font-size: 13px;
        animation: slideUp 0.3s ease-out;
        max-width: 320px;
    }}
    .toast.success {{ border-left: 4px solid {c['success']}; }}
    .toast.error   {{ border-left: 4px solid {c['danger']}; }}
    .toast.info    {{ border-left: 4px solid {c['info']}; }}

    /* ── Welcome screen ───────────────────────────────────────── */
    .welcome-wrapper {{
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        min-height: 60vh;
        text-align: center;
        padding: 2rem;
    }}
    .welcome-logo {{
        font-size: 52px;
        margin-bottom: 1rem;
        animation: fadeIn 0.5s ease-in;
    }}
    .welcome-title {{
        font-size: 28px;
        font-weight: 700;
        color: {c['text_primary']};
        margin-bottom: 0.5rem;
    }}
    .welcome-subtitle {{
        font-size: 15px;
        color: {c['text_secondary']};
        margin-bottom: 2rem;
        max-width: 480px;
    }}

    /* ── Sidebar conversation item ────────────────────────────── */
    .conv-item {{
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.5rem 0.6rem;
        border-radius: 8px;
        cursor: pointer;
        font-size: 13px;
        color: {c['text_secondary']};
        transition: background 0.15s, color 0.15s;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }}
    .conv-item:hover {{
        background: {c['border']};
        color: {c['text_primary']};
    }}
    .conv-item.active {{
        background: {c['accent_light']};
        color: {c['accent']};
        font-weight: 600;
    }}

    /* ── Divider ──────────────────────────────────────────────── */
    .section-divider {{
        border: none;
        border-top: 1px solid {c['border']};
        margin: 0.75rem 0;
    }}

    /* ── Keyframes ────────────────────────────────────────────── */
    @keyframes fadeIn {{
        from {{ opacity: 0; transform: translateY(6px); }}
        to   {{ opacity: 1; transform: translateY(0); }}
    }}
    @keyframes shimmer {{
        from {{ background-position: 200% 0; }}
        to   {{ background-position: -200% 0; }}
    }}
    @keyframes bounce {{
        0%, 60%, 100% {{ transform: translateY(0); }}
        30%            {{ transform: translateY(-6px); }}
    }}
    @keyframes pulse {{
        0%, 100% {{ opacity: 1; }}
        50%       {{ opacity: 0.4; }}
    }}
    @keyframes slideUp {{
        from {{ opacity: 0; transform: translateY(16px); }}
        to   {{ opacity: 1; transform: translateY(0); }}
    }}

    /* ── Responsive ───────────────────────────────────────────── */
    @media (max-width: 900px) {{
        .bubble {{ max-width: 90%; }}
        .welcome-title {{ font-size: 22px; }}
    }}
    @media (max-width: 600px) {{
        .bubble {{ max-width: 95%; }}
        .input-inner {{ flex-direction: column; }}
    }}

    /* ── Streamlit element overrides ──────────────────────────── */
    [data-testid="stMarkdownContainer"] p {{
        margin: 0.25rem 0;
    }}
    div[data-testid="stExpander"] {{
        background: {c['bg_secondary']} !important;
        border: 1px solid {c['border']} !important;
        border-radius: 10px !important;
    }}
    [data-testid="stSelectbox"] > div,
    [data-testid="stSlider"]    > div {{
        color: {c['text_primary']} !important;
    }}
    .stRadio label, .stCheckbox label {{
        color: {c['text_primary']} !important;
    }}

    /* ── st.chat_input overrides ──────────────────────────────── */
    [data-testid="stChatInput"] {{
        background: {c['bg_input']} !important;
        border: 1px solid {c['border']} !important;
        border-radius: 14px !important;
        box-shadow: 0 2px 12px {c['shadow']} !important;
    }}
    [data-testid="stChatInput"] textarea {{
        background: {c['bg_input']} !important;
        color: {c['text_primary']} !important;
        font-size: 15px !important;
        font-family: 'Inter', 'Segoe UI', system-ui, sans-serif !important;
    }}
    [data-testid="stChatInput"] textarea::placeholder {{
        color: {c['text_muted']} !important;
    }}
    [data-testid="stChatInput"] button {{
        background: {c['accent']} !important;
        color: #fff !important;
        border-radius: 10px !important;
    }}
    [data-testid="stChatInput"] button:hover {{
        background: {c['accent_hover']} !important;
    }}

    /* ── st.chat_message overrides ────────────────────────────── */
    [data-testid="stChatMessage"] {{
        background: transparent !important;
        border: none !important;
        padding: 0.25rem 0 !important;
        animation: fadeIn 0.2s ease-in-out;
    }}
    /* User bubble */
    [data-testid="stChatMessage"][data-testid*="user"] {{
        flex-direction: row-reverse;
    }}
    [data-testid="stChatMessageContent"] {{
        background: transparent !important;
    }}

    /* ── st.status widget ─────────────────────────────────────── */
    [data-testid="stStatus"] {{
        background: {c['bg_secondary']} !important;
        border: 1px solid {c['border']} !important;
        border-radius: 12px !important;
        font-size: 13px !important;
    }}

    /* ── Main content padding for chat ───────────────────────── */
    .main .block-container {{
        padding: 1rem 1.5rem 1rem !important;
        max-width: 100% !important;
    }}

    /* ── Sidebar width ────────────────────────────────────────── */
    [data-testid="stSidebar"] {{
        min-width: 260px !important;
        max-width: 300px !important;
    }}

    /* ── Action button row (copy/like/dislike/regen) ──────────── */
    .msg-actions {{
        display: flex;
        gap: 4px;
        margin-top: 2px;
        margin-left: 48px;
        opacity: 0;
        transition: opacity 0.2s;
    }}
    .msg-actions:hover {{ opacity: 1; }}
    [data-testid="stChatMessage"]:hover + .msg-actions,
    [data-testid="stChatMessage"]:focus-within + .msg-actions {{
        opacity: 1;
    }}
    .msg-actions .stButton > button {{
        padding: 2px 8px !important;
        font-size: 12px !important;
        height: 28px !important;
        min-height: 28px !important;
        border-radius: 6px !important;
        background: {c['bg_secondary']} !important;
        border: 1px solid {c['border']} !important;
        color: {c['text_secondary']} !important;
    }}
    .msg-actions .stButton > button:hover {{
        background: {c['border']} !important;
        color: {c['text_primary']} !important;
    }}

    /* ── Processing status banner ─────────────────────────────── */
    .processing-banner {{
        background: linear-gradient(90deg, {c['accent_light']}, {c['bg_secondary']});
        border: 1px solid {c['accent']};
        border-radius: 10px;
        padding: 0.6rem 1rem;
        font-size: 13px;
        color: {c['accent']};
        display: flex;
        align-items: center;
        gap: 0.5rem;
        margin: 0.5rem 0;
        animation: fadeIn 0.3s ease;
    }}

    /* ── Conversation metadata label ──────────────────────────── */
    .msg-timestamp {{
        font-size: 10px;
        color: {c['text_muted']};
        margin-top: 2px;
        padding-left: 48px;
    }}
    """


def apply_theme(dark_mode: bool = False) -> None:
    """
    Inject the compiled CSS into the Streamlit page.

    Call once at the very top of ``app.py`` after
    ``st.set_page_config()``.

    Parameters
    ----------
    dark_mode : bool
        When True the dark palette is used.
    """
    palette = get_palette(dark_mode)
    css = build_css(palette)
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
