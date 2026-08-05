"""
3D Design System — AI Research Workspace.
Combines config.toml dark base with injected CSS for 3D depth, neon glows,
glassmorphism, and premium visual hierarchy.

Root cause of previous failure: no .streamlit/config.toml existed so
Streamlit rendered in light mode and overrode injected dark styles.
Solution: config.toml forces dark base; this file adds 3D depth on top.
"""

COLORS = {
    "bg0":     "#080c18",   # deepest background
    "bg1":     "#0d1426",   # card background
    "bg2":     "#111e36",   # elevated surface
    "bg3":     "#172240",   # hover surface
    "border":  "#1e3058",
    "glow_b":  "rgba(79,142,247,0.35)",
    "glow_p":  "rgba(139,92,246,0.35)",
    "glow_c":  "rgba(6,182,212,0.3)",
    "blue":    "#4f8ef7",
    "indigo":  "#6366f1",
    "purple":  "#8b5cf6",
    "cyan":    "#06b6d4",
    "teal":    "#14b8a6",
    "green":   "#22c55e",
    "amber":   "#f59e0b",
    "red":     "#ef4444",
    "text0":   "#f0f6ff",
    "text1":   "#94a3b8",
    "text2":   "#4a5568",
}

PLAN_GRADIENTS = {
    "free":       "linear-gradient(135deg,#374151,#1f2937)",
    "pro":        "linear-gradient(135deg,#7c3aed,#4f8ef7)",
    "enterprise": "linear-gradient(135deg,#d97706,#f59e0b)",
}

# ── 3D CSS Part 1: Reset, fonts, page background ─────────────────────────────
_CSS_PART1 = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:ital,wght@0,300;0,400;0,500;0,600;0,700;0,800;1,400&family=JetBrains+Mono:wght@400;500&display=swap');

*, *::before, *::after { box-sizing: border-box; }

/* Force dark background on every Streamlit container */
.stApp,
.stApp > header,
[data-testid="stAppViewContainer"],
[data-testid="stHeader"],
[data-testid="stMain"],
.main,
.block-container {
    background-color: #080c18 !important;
    background-image:
        radial-gradient(ellipse at 15% 20%, rgba(79,142,247,0.06) 0%, transparent 55%),
        radial-gradient(ellipse at 85% 80%, rgba(139,92,246,0.05) 0%, transparent 55%),
        radial-gradient(ellipse at 50% 50%, rgba(6,182,212,0.02) 0%, transparent 70%)
        !important;
}

.block-container {
    padding: 1.5rem 2.2rem 2rem !important;
    max-width: 1440px !important;
}

html, body, [class*="css"], p, span, div, label {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont,
                 'Segoe UI', sans-serif !important;
    -webkit-font-smoothing: antialiased !important;
}

/* Scrollbar */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: #080c18; }
::-webkit-scrollbar-thumb {
    background: linear-gradient(180deg,#4f8ef7,#8b5cf6);
    border-radius: 3px;
}
</style>
"""

# ── 3D CSS Part 2: Sidebar ────────────────────────────────────────────────────
_CSS_PART2 = """
<style>
/* Sidebar — 3D depth panel */
[data-testid="stSidebar"],
[data-testid="stSidebar"] > div:first-child {
    background: linear-gradient(180deg,#060a14 0%,#080c18 40%,#0a0f1e 100%) !important;
    border-right: 1px solid rgba(79,142,247,0.18) !important;
    box-shadow: 4px 0 32px rgba(0,0,0,0.6), inset -1px 0 0 rgba(79,142,247,0.06) !important;
}

/* Sidebar all buttons */
[data-testid="stSidebar"] .stButton > button {
    background: transparent !important;
    border: 1px solid transparent !important;
    color: #6b7280 !important;
    border-radius: 8px !important;
    font-size: 0.875rem !important;
    font-weight: 500 !important;
    padding: 8px 12px !important;
    transition: all 0.18s cubic-bezier(0.4,0,0.2,1) !important;
    text-align: left !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(79,142,247,0.1) !important;
    border-color: rgba(79,142,247,0.25) !important;
    color: #e8eeff !important;
    box-shadow: 0 2px 12px rgba(79,142,247,0.15), inset 0 1px 0 rgba(255,255,255,0.04) !important;
    transform: translateX(2px) !important;
}

/* Sidebar text & captions */
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] div {
    color: #6b7280 !important;
}
[data-testid="stSidebar"] .stMarkdown p { color: #94a3b8 !important; }

/* Sidebar expander */
[data-testid="stSidebar"] .streamlit-expanderHeader {
    background: rgba(17,30,54,0.5) !important;
    border: 1px solid rgba(30,48,88,0.6) !important;
    border-radius: 8px !important;
    color: #6b7280 !important;
}
[data-testid="stSidebar"] .streamlit-expanderContent {
    background: rgba(13,20,38,0.6) !important;
    border: 1px solid rgba(30,48,88,0.4) !important;
    border-top: none !important;
    border-radius: 0 0 8px 8px !important;
}

/* Sidebar selectbox */
[data-testid="stSidebar"] [data-baseweb="select"] > div {
    background: rgba(17,30,54,0.7) !important;
    border: 1px solid rgba(30,48,88,0.8) !important;
    border-radius: 8px !important;
    color: #94a3b8 !important;
}
[data-testid="stSidebar"] [data-baseweb="select"] svg { fill: #6b7280 !important; }
</style>
"""

# ── 3D CSS Part 3: Buttons ────────────────────────────────────────────────────
_CSS_PART3 = """
<style>
/* PRIMARY — 3D gradient with neon glow */
.stButton > button[kind="primary"],
button[data-testid*="baseButton-primary"],
[data-testid="stFormSubmitButton"] > button {
    background: linear-gradient(135deg, #4f8ef7 0%, #7c3aed 100%) !important;
    border: 1px solid rgba(139,92,246,0.4) !important;
    color: #ffffff !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    font-size: 0.9rem !important;
    padding: 10px 22px !important;
    letter-spacing: 0.02em !important;
    box-shadow:
        0 4px 15px rgba(79,142,247,0.35),
        0 2px 4px rgba(0,0,0,0.4),
        inset 0 1px 0 rgba(255,255,255,0.15),
        inset 0 -1px 0 rgba(0,0,0,0.2) !important;
    transition: all 0.2s cubic-bezier(0.4,0,0.2,1) !important;
    position: relative !important;
    transform: translateY(0) !important;
}
.stButton > button[kind="primary"]:hover,
button[data-testid*="baseButton-primary"]:hover {
    background: linear-gradient(135deg, #6aa0ff 0%, #9b59ff 100%) !important;
    box-shadow:
        0 8px 25px rgba(79,142,247,0.5),
        0 4px 8px rgba(0,0,0,0.4),
        inset 0 1px 0 rgba(255,255,255,0.2) !important;
    transform: translateY(-2px) !important;
}
.stButton > button[kind="primary"]:active {
    transform: translateY(0) !important;
    box-shadow: 0 2px 8px rgba(79,142,247,0.3) !important;
}

/* SECONDARY */
.stButton > button[kind="secondary"],
button[data-testid*="baseButton-secondary"] {
    background: rgba(17,30,54,0.8) !important;
    border: 1px solid rgba(30,48,88,0.9) !important;
    color: #94a3b8 !important;
    border-radius: 10px !important;
    font-weight: 500 !important;
    font-size: 0.875rem !important;
    padding: 9px 18px !important;
    box-shadow:
        0 2px 8px rgba(0,0,0,0.3),
        inset 0 1px 0 rgba(255,255,255,0.04),
        inset 0 -1px 0 rgba(0,0,0,0.15) !important;
    transition: all 0.18s ease !important;
}
.stButton > button[kind="secondary"]:hover {
    background: rgba(79,142,247,0.1) !important;
    border-color: rgba(79,142,247,0.35) !important;
    color: #e8eeff !important;
    box-shadow:
        0 4px 16px rgba(79,142,247,0.2),
        inset 0 1px 0 rgba(255,255,255,0.06) !important;
    transform: translateY(-1px) !important;
}

/* DOWNLOAD */
[data-testid="stDownloadButton"] > button {
    background: rgba(16,185,129,0.12) !important;
    border: 1px solid rgba(16,185,129,0.3) !important;
    color: #22c55e !important;
    border-radius: 10px !important;
    box-shadow: 0 2px 12px rgba(16,185,129,0.15) !important;
}
[data-testid="stDownloadButton"] > button:hover {
    background: rgba(16,185,129,0.2) !important;
    box-shadow: 0 4px 20px rgba(16,185,129,0.25) !important;
    transform: translateY(-1px) !important;
}
</style>
"""

# ── 3D CSS Part 4: Inputs, Forms ──────────────────────────────────────────────
_CSS_PART4 = """
<style>
/* Text inputs */
.stTextInput input,
.stTextInput > div > div > input,
[data-testid="stTextInput"] input {
    background: rgba(13,20,38,0.9) !important;
    border: 1px solid rgba(30,48,88,0.9) !important;
    border-radius: 10px !important;
    color: #e8eeff !important;
    font-size: 0.92rem !important;
    padding: 10px 14px !important;
    box-shadow: inset 0 2px 8px rgba(0,0,0,0.3), inset 0 1px 0 rgba(0,0,0,0.2) !important;
    transition: all 0.2s ease !important;
}
.stTextInput input:focus,
[data-testid="stTextInput"] input:focus {
    border-color: #4f8ef7 !important;
    box-shadow:
        inset 0 2px 8px rgba(0,0,0,0.3),
        0 0 0 3px rgba(79,142,247,0.15),
        0 0 20px rgba(79,142,247,0.1) !important;
    outline: none !important;
}

/* TextArea */
.stTextArea textarea,
[data-testid="stTextArea"] textarea {
    background: rgba(13,20,38,0.9) !important;
    border: 1px solid rgba(30,48,88,0.9) !important;
    border-radius: 10px !important;
    color: #e8eeff !important;
    font-size: 0.92rem !important;
    box-shadow: inset 0 2px 8px rgba(0,0,0,0.3) !important;
    transition: all 0.2s ease !important;
}
.stTextArea textarea:focus {
    border-color: #4f8ef7 !important;
    box-shadow: inset 0 2px 8px rgba(0,0,0,0.3), 0 0 0 3px rgba(79,142,247,0.15) !important;
}

/* Selectbox */
[data-baseweb="select"] > div,
.stSelectbox > div > div {
    background: rgba(13,20,38,0.9) !important;
    border: 1px solid rgba(30,48,88,0.9) !important;
    border-radius: 10px !important;
    color: #e8eeff !important;
    box-shadow: inset 0 2px 8px rgba(0,0,0,0.3) !important;
}
[data-baseweb="select"] [data-testid="stSelectbox"] { color: #e8eeff !important; }
[data-baseweb="popover"] {
    background: #0d1426 !important;
    border: 1px solid rgba(30,48,88,0.9) !important;
    box-shadow: 0 20px 60px rgba(0,0,0,0.6), 0 0 0 1px rgba(79,142,247,0.08) !important;
}
[data-baseweb="popover"] li { color: #94a3b8 !important; }
[data-baseweb="popover"] li:hover {
    background: rgba(79,142,247,0.1) !important;
    color: #e8eeff !important;
}

/* Chat input — most critical */
[data-testid="stChatInput"],
[data-testid="stChatInput"] > div {
    background: rgba(13,20,38,0.95) !important;
    border: 1px solid rgba(30,48,88,0.9) !important;
    border-radius: 16px !important;
    box-shadow:
        0 -4px 24px rgba(0,0,0,0.4),
        inset 0 1px 0 rgba(255,255,255,0.03) !important;
}
[data-testid="stChatInput"]:focus-within,
[data-testid="stChatInput"] > div:focus-within {
    border-color: rgba(79,142,247,0.5) !important;
    box-shadow:
        0 -4px 24px rgba(0,0,0,0.4),
        0 0 0 3px rgba(79,142,247,0.12),
        0 0 30px rgba(79,142,247,0.08) !important;
}
[data-testid="stChatInput"] textarea {
    background: transparent !important;
    border: none !important;
    color: #e8eeff !important;
    font-size: 0.95rem !important;
    box-shadow: none !important;
}

/* Forms */
[data-testid="stForm"] {
    background: rgba(13,20,38,0.6) !important;
    border: 1px solid rgba(30,48,88,0.6) !important;
    border-radius: 16px !important;
    padding: 20px !important;
    box-shadow: 0 8px 32px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.03) !important;
}

/* Label text */
.stTextInput > label,
.stTextArea > label,
.stSelectbox > label,
label[data-testid="stWidgetLabel"],
p[data-testid="stWidgetLabel"] {
    color: #94a3b8 !important;
    font-size: 0.84rem !important;
    font-weight: 500 !important;
    letter-spacing: 0.02em !important;
}

/* File uploader */
[data-testid="stFileUploader"] > section {
    background: rgba(13,20,38,0.7) !important;
    border: 2px dashed rgba(30,48,88,0.9) !important;
    border-radius: 14px !important;
    transition: all 0.2s ease !important;
}
[data-testid="stFileUploader"] > section:hover {
    border-color: rgba(79,142,247,0.5) !important;
    background: rgba(79,142,247,0.04) !important;
    box-shadow: 0 0 30px rgba(79,142,247,0.06) !important;
}
[data-testid="stFileUploader"] label { color: #94a3b8 !important; }
</style>
"""

# ── 3D CSS Part 5: Chat messages, tabs, expanders ─────────────────────────────
_CSS_PART5 = """
<style>
/* Chat messages — 3D bubbles */
[data-testid="stChatMessage"] {
    border-radius: 16px !important;
    padding: 14px 18px !important;
    margin: 8px 0 !important;
    border: 1px solid transparent !important;
    animation: msg-in 0.25s cubic-bezier(0.4,0,0.2,1) !important;
}
/* User bubble */
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
    background: linear-gradient(135deg,rgba(79,142,247,0.1),rgba(99,102,241,0.08)) !important;
    border-color: rgba(79,142,247,0.2) !important;
    box-shadow: 0 4px 20px rgba(79,142,247,0.08), inset 0 1px 0 rgba(79,142,247,0.08) !important;
}
/* Assistant bubble */
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) {
    background: linear-gradient(135deg,rgba(13,20,38,0.9),rgba(17,30,54,0.8)) !important;
    border-color: rgba(30,48,88,0.7) !important;
    box-shadow: 0 4px 20px rgba(0,0,0,0.2), inset 0 1px 0 rgba(255,255,255,0.03) !important;
}
/* Avatar icons */
[data-testid="chatAvatarIcon-user"] {
    background: linear-gradient(135deg,#4f8ef7,#7c3aed) !important;
    border: none !important;
    box-shadow: 0 2px 10px rgba(79,142,247,0.4) !important;
}
[data-testid="chatAvatarIcon-assistant"] {
    background: linear-gradient(135deg,#0d1426,#111e36) !important;
    border: 1px solid rgba(30,48,88,0.8) !important;
    box-shadow: 0 2px 10px rgba(0,0,0,0.3) !important;
}

/* Tabs */
[data-baseweb="tab-list"] {
    background: rgba(13,20,38,0.6) !important;
    border: 1px solid rgba(30,48,88,0.6) !important;
    border-radius: 12px !important;
    padding: 4px !important;
    gap: 2px !important;
}
[data-baseweb="tab"] {
    background: transparent !important;
    border-radius: 8px !important;
    color: #6b7280 !important;
    font-weight: 500 !important;
    font-size: 0.88rem !important;
    padding: 8px 18px !important;
    border: 1px solid transparent !important;
    transition: all 0.18s ease !important;
}
[data-baseweb="tab"]:hover {
    color: #94a3b8 !important;
    background: rgba(79,142,247,0.06) !important;
}
[aria-selected="true"][data-baseweb="tab"] {
    background: linear-gradient(135deg,rgba(79,142,247,0.18),rgba(139,92,246,0.12)) !important;
    border-color: rgba(79,142,247,0.3) !important;
    color: #e8eeff !important;
    box-shadow: 0 2px 12px rgba(79,142,247,0.15), inset 0 1px 0 rgba(255,255,255,0.06) !important;
}

/* Expanders */
.streamlit-expanderHeader {
    background: rgba(17,30,54,0.7) !important;
    border: 1px solid rgba(30,48,88,0.7) !important;
    border-radius: 10px !important;
    color: #94a3b8 !important;
    font-size: 0.88rem !important;
    transition: all 0.15s ease !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.2) !important;
}
.streamlit-expanderHeader:hover {
    background: rgba(79,142,247,0.08) !important;
    border-color: rgba(79,142,247,0.25) !important;
    color: #e8eeff !important;
}
.streamlit-expanderContent {
    background: rgba(13,20,38,0.7) !important;
    border: 1px solid rgba(30,48,88,0.6) !important;
    border-top: none !important;
    border-radius: 0 0 10px 10px !important;
    box-shadow: inset 0 4px 12px rgba(0,0,0,0.15) !important;
}

/* Progress bar */
.stProgress > div > div { background: rgba(30,48,88,0.6) !important; border-radius: 4px !important; height: 6px !important; }
.stProgress > div > div > div { background: linear-gradient(90deg,#4f8ef7,#7c3aed) !important; border-radius: 4px !important; box-shadow: 0 0 10px rgba(79,142,247,0.4) !important; }

/* Alerts */
[data-testid="stAlert"] { border-radius: 12px !important; border-width: 1px !important; }
[data-baseweb="notification"][kind="info"]    { background: rgba(59,130,246,0.1) !important; border-color: rgba(59,130,246,0.25) !important; }
[data-baseweb="notification"][kind="success"] { background: rgba(34,197,94,0.1)  !important; border-color: rgba(34,197,94,0.25)  !important; }
[data-baseweb="notification"][kind="warning"] { background: rgba(245,158,11,0.1) !important; border-color: rgba(245,158,11,0.25) !important; }
[data-baseweb="notification"][kind="error"]   { background: rgba(239,68,68,0.1)  !important; border-color: rgba(239,68,68,0.25)  !important; }
div[data-testid="stAlert"] { box-shadow: 0 4px 20px rgba(0,0,0,0.2) !important; }
</style>
"""

# ── 3D CSS Part 6: Typography, dataframes, metrics, dividers ─────────────────
_CSS_PART6 = """
<style>
/* Headings */
h1 { color: #f0f6ff !important; font-weight: 800 !important; font-size: 1.85rem !important; letter-spacing: -0.02em !important; }
h2 { color: #e2eaff !important; font-weight: 700 !important; font-size: 1.4rem  !important; }
h3 { color: #c8d8ff !important; font-weight: 600 !important; font-size: 1.1rem  !important; }
h4 { color: #94a3b8 !important; font-weight: 600 !important; font-size: 0.95rem !important; }
p, li, span { color: #94a3b8 !important; font-size: 0.92rem !important; line-height: 1.7 !important; }
a { color: #60a5fa !important; text-decoration: none !important; }
a:hover { color: #93c5fd !important; text-shadow: 0 0 12px rgba(96,165,250,0.4) !important; }
strong { color: #e8eeff !important; font-weight: 600 !important; }
em { color: #94a3b8 !important; }

code {
    background: rgba(79,142,247,0.1) !important;
    color: #93c5fd !important;
    border: 1px solid rgba(79,142,247,0.2) !important;
    border-radius: 5px !important;
    padding: 2px 7px !important;
    font-family: 'JetBrains Mono', 'Fira Code', monospace !important;
    font-size: 0.84em !important;
}
pre {
    background: #060a14 !important;
    border: 1px solid rgba(30,48,88,0.8) !important;
    border-radius: 12px !important;
    box-shadow: inset 0 2px 12px rgba(0,0,0,0.4), 0 4px 20px rgba(0,0,0,0.3) !important;
}
pre code {
    background: transparent !important;
    border: none !important;
    padding: 0 !important;
    font-size: 0.88rem !important;
}

hr {
    border: none !important;
    height: 1px !important;
    background: linear-gradient(90deg,transparent,rgba(30,48,88,0.8),transparent) !important;
    margin: 20px 0 !important;
}

/* Dataframes / tables */
[data-testid="stDataFrame"] {
    border: 1px solid rgba(30,48,88,0.7) !important;
    border-radius: 14px !important;
    overflow: hidden !important;
    box-shadow: 0 8px 32px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.02) !important;
}
[data-testid="stDataFrame"] table { background: rgba(8,12,24,0.9) !important; }
[data-testid="stDataFrame"] thead th {
    background: rgba(13,20,38,0.95) !important;
    color: #6b7280 !important;
    font-size: 0.75rem !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.08em !important;
    border-bottom: 1px solid rgba(30,48,88,0.8) !important;
    padding: 12px 16px !important;
}
[data-testid="stDataFrame"] tbody td {
    color: #94a3b8 !important;
    font-size: 0.875rem !important;
    border-bottom: 1px solid rgba(17,30,54,0.8) !important;
    padding: 10px 16px !important;
}
[data-testid="stDataFrame"] tbody tr:hover td {
    background: rgba(79,142,247,0.04) !important;
    color: #e8eeff !important;
}

/* Metrics */
[data-testid="metric-container"],
[data-testid="stMetric"] {
    background: linear-gradient(145deg,#111e36,#0d1426) !important;
    border: 1px solid rgba(30,48,88,0.7) !important;
    border-radius: 14px !important;
    padding: 18px 22px !important;
    box-shadow: 0 4px 20px rgba(0,0,0,0.25), inset 0 1px 0 rgba(255,255,255,0.03) !important;
    transition: all 0.2s ease !important;
}
[data-testid="metric-container"]:hover {
    border-color: rgba(79,142,247,0.25) !important;
    box-shadow: 0 8px 30px rgba(0,0,0,0.35), 0 0 20px rgba(79,142,247,0.06) !important;
    transform: translateY(-1px) !important;
}
[data-testid="stMetricValue"] { color: #f0f6ff !important; font-weight: 700 !important; }
[data-testid="stMetricLabel"] { color: #6b7280 !important; font-size: 0.76rem !important; text-transform: uppercase !important; letter-spacing: 0.08em !important; }
[data-testid="stMetricDelta"] { font-size: 0.8rem !important; font-weight: 600 !important; }

/* Caption */
.stCaption, [data-testid="stCaptionContainer"] p {
    color: #4a5568 !important;
    font-size: 0.78rem !important;
}

/* Spinner */
[data-testid="stSpinner"] > div > div {
    border-top-color: #4f8ef7 !important;
    filter: drop-shadow(0 0 6px rgba(79,142,247,0.4)) !important;
}

/* Page links */
[data-testid="stPageLink"] a {
    background: transparent !important;
    border: 1px solid transparent !important;
    color: #6b7280 !important;
    border-radius: 8px !important;
    padding: 7px 12px !important;
    font-size: 0.875rem !important;
    display: flex !important;
    align-items: center !important;
    gap: 8px !important;
    transition: all 0.15s ease !important;
}
[data-testid="stPageLink"] a:hover {
    background: rgba(79,142,247,0.1) !important;
    border-color: rgba(79,142,247,0.25) !important;
    color: #e8eeff !important;
    text-decoration: none !important;
    box-shadow: 0 2px 12px rgba(79,142,247,0.12) !important;
}
</style>
"""

# ── 3D CSS Part 7: Animations & utility classes ───────────────────────────────
_CSS_PART7 = """
<style>
/* Keyframes */
@keyframes msg-in {
    from { opacity: 0; transform: translateY(14px); }
    to   { opacity: 1; transform: translateY(0); }
}
@keyframes fade-in {
    from { opacity: 0; }
    to   { opacity: 1; }
}
@keyframes slide-up {
    from { opacity: 0; transform: translateY(20px); }
    to   { opacity: 1; transform: translateY(0); }
}
@keyframes pulse-glow {
    0%, 100% { box-shadow: 0 0 12px rgba(79,142,247,0.25); }
    50%       { box-shadow: 0 0 24px rgba(79,142,247,0.5); }
}
@keyframes shimmer {
    0%   { background-position: -200% 0; }
    100% { background-position:  200% 0; }
}

/* Skeleton loaders */
.skeleton {
    background: linear-gradient(90deg, #0d1426 25%, #172240 50%, #0d1426 75%);
    background-size: 200% 100%;
    animation: shimmer 1.6s ease-in-out infinite;
    border-radius: 8px;
}

/* Typing indicator dots */
.typing-dot {
    display: inline-block;
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: #4f8ef7;
    margin: 0 2px;
    animation: pulse-glow 1.2s ease-in-out infinite;
    box-shadow: 0 0 6px rgba(79,142,247,0.4);
}
.typing-dot:nth-child(2) { animation-delay: 0.2s; }
.typing-dot:nth-child(3) { animation-delay: 0.4s; }

/* 3D card helper */
.card-3d {
    background: linear-gradient(145deg, #111e36, #0d1426) !important;
    border: 1px solid rgba(30,48,88,0.7) !important;
    border-radius: 16px !important;
    box-shadow:
        0 8px 32px rgba(0,0,0,0.35),
        inset 0 1px 0 rgba(255,255,255,0.04),
        inset 0 -1px 0 rgba(0,0,0,0.2) !important;
    transition: all 0.2s ease !important;
}
.card-3d:hover {
    transform: translateY(-2px) !important;
    box-shadow:
        0 12px 40px rgba(0,0,0,0.45),
        0 0 24px rgba(79,142,247,0.08),
        inset 0 1px 0 rgba(255,255,255,0.06) !important;
    border-color: rgba(79,142,247,0.25) !important;
}

/* Glass panel */
.glass-panel {
    background: rgba(13,20,38,0.88) !important;
    backdrop-filter: blur(14px) !important;
    -webkit-backdrop-filter: blur(14px) !important;
    border: 1px solid rgba(30,48,88,0.6) !important;
    border-radius: 16px !important;
    box-shadow: 0 12px 48px rgba(0,0,0,0.4) !important;
}

/* Neon glow utilities */
.glow-blue   { box-shadow: 0 0 20px rgba(79,142,247,0.35), 0 0 40px rgba(79,142,247,0.15) !important; }
.glow-purple { box-shadow: 0 0 20px rgba(139,92,246,0.35), 0 0 40px rgba(139,92,246,0.15) !important; }
.glow-cyan   { box-shadow: 0 0 20px rgba(6,182,212,0.35),  0 0 40px rgba(6,182,212,0.15) !important; }
.glow-green  { box-shadow: 0 0 20px rgba(34,197,94,0.35),  0 0 40px rgba(34,197,94,0.15) !important; }
.glow-red    { box-shadow: 0 0 20px rgba(239,68,68,0.35),  0 0 40px rgba(239,68,68,0.15) !important; }
.glow-amber  { box-shadow: 0 0 20px rgba(245,158,11,0.35), 0 0 40px rgba(245,158,11,0.15) !important; }

/* Section divider */
.section-divider {
    border: none !important;
    height: 1px !important;
    background: linear-gradient(90deg, transparent 0%, rgba(79,142,247,0.3) 50%, transparent 100%) !important;
    margin: 28px 0 !important;
}

/* Empty state */
.empty-state {
    text-align: center;
    padding: 48px 24px;
    animation: fade-in 0.4s ease;
}
.empty-state-icon { font-size: 4rem; margin-bottom: 16px; opacity: 0.45; filter: drop-shadow(0 4px 12px rgba(79,142,247,0.15)); }
.empty-state-title { color: #f0f6ff; font-size: 1.15rem; font-weight: 600; margin-bottom: 8px; }
.empty-state-desc { color: #4a5568; font-size: 0.88rem; max-width: 380px; margin: 0 auto; }

/* Tool badge */
.tool-badge {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    background: rgba(79,142,247,0.12);
    border: 1px solid rgba(79,142,247,0.25);
    border-radius: 20px;
    padding: 4px 11px;
    font-size: 0.78rem;
    font-weight: 600;
    color: #93c5fd;
    box-shadow: 0 2px 8px rgba(79,142,247,0.15);
}
</style>
"""


# ── Aggregated global CSS ─────────────────────────────────────────────────────
GLOBAL_CSS = _CSS_PART1 + _CSS_PART2 + _CSS_PART3 + _CSS_PART4 + _CSS_PART5 + _CSS_PART6 + _CSS_PART7


def inject_global_css():
    """Inject all 3D CSS. Call ONCE at top of each page after st.set_page_config()."""
    import streamlit as st
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)


def inject_page_bg():
    """Ensure the root app container uses the 3D gradient background."""
    import streamlit as st
    st.markdown(
        """<style>
.stApp, .main, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
    background: #080c18 !important;
    background-image:
        radial-gradient(ellipse at 12% 18%, rgba(79,142,247,0.07) 0%, transparent 50%),
        radial-gradient(ellipse at 88% 82%, rgba(139,92,246,0.06) 0%, transparent 50%),
        radial-gradient(ellipse at 50% 50%, rgba(6,182,212,0.03) 0%, transparent 65%) !important;
}
</style>""",
        unsafe_allow_html=True,
    )


PLAN_COLORS = {
    "free":       COLORS["text1"],
    "pro":        COLORS["purple"],
    "enterprise": COLORS["amber"],
}


# ── Light Theme CSS (injected when theme_mode == "light") ─────────────────────
_LIGHT_CSS = """
<style>
/* Light theme overrides */
.stApp, .stApp > header, [data-testid="stAppViewContainer"], .main, .block-container {
    background: #f5f7fb !important;
    background-image:
        radial-gradient(ellipse at 15% 20%, rgba(79,142,247,0.08) 0%, transparent 55%),
        radial-gradient(ellipse at 85% 80%, rgba(139,92,246,0.06) 0%, transparent 55%) !important;
}

[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%) !important;
    border-right: 1px solid rgba(0,0,0,0.08) !important;
    box-shadow: 4px 0 24px rgba(0,0,0,0.08) !important;
}

[data-testid="stSidebar"] .stButton > button {
    color: #475569 !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(79,142,247,0.08) !important;
    color: #0f172a !important;
}

.stTextInput input,
.stTextArea textarea,
[data-testid="stChatInput"] {
    background: #ffffff !important;
    border-color: rgba(0,0,0,0.12) !important;
    color: #0f172a !important;
}

.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #4f8ef7 0%, #7c3aed 100%) !important;
    color: #ffffff !important;
}

.stButton > button[kind="secondary"] {
    background: #ffffff !important;
    border-color: rgba(0,0,0,0.12) !important;
    color: #475569 !important;
}

h1, h2, h3, h4 { color: #0f172a !important; }
p, li, span { color: #475569 !important; }
a { color: #2563eb !important; }
code {
    background: rgba(79,142,247,0.1) !important;
    color: #1e40af !important;
}

[data-testid="stChatMessage"] {
    background: #ffffff !important;
    border-color: rgba(0,0,0,0.08) !important;
}
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
    background: rgba(79,142,247,0.06) !important;
}

[data-testid="metric-container"],
[data-testid="stMetric"] {
    background: #ffffff !important;
    border-color: rgba(0,0,0,0.08) !important;
}

[data-testid="stDataFrame"] table { background: #ffffff !important; }
[data-testid="stDataFrame"] thead th { background: #f8fafc !important; color: #475569 !important; }
[data-testid="stDataFrame"] tbody td { color: #0f172a !important; }
</style>
"""


def inject_light_theme():
    """Inject light theme CSS overrides."""
    import streamlit as st
    st.markdown(_LIGHT_CSS, unsafe_allow_html=True)
