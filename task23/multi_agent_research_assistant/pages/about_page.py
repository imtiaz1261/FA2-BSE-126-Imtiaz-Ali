"""
pages/about_page.py
--------------------
About / information page for the Multi-Agent Research Assistant.

Contains
--------
- Project overview
- Architecture diagram (text-based)
- Technology stack cards
- Agent descriptions
- Version & build info
"""

from __future__ import annotations

import streamlit as st


# ── Tech stack ────────────────────────────────────────────────────────────────

_TECH_STACK: list[dict[str, str]] = [
    {"icon": "🦜", "name": "LangChain",   "desc": "LLM application framework"},
    {"icon": "🕸️", "name": "LangGraph",   "desc": "Multi-agent orchestration"},
    {"icon": "🤖", "name": "OpenAI GPT",  "desc": "Primary language model"},
    {"icon": "💎", "name": "Google Gemini","desc": "Alternative LLM provider"},
    {"icon": "🔍", "name": "Tavily",       "desc": "Real-time web search API"},
    {"icon": "🌐", "name": "Streamlit",    "desc": "Web interface framework"},
    {"icon": "✅", "name": "Pydantic",     "desc": "Data validation & settings"},
    {"icon": "📄", "name": "python-docx",  "desc": "DOCX export"},
]

_AGENTS_INFO: list[dict[str, str]] = [
    {
        "icon":  "🔍",
        "name":  "Researcher Agent",
        "role":  "Information Gathering",
        "desc": (
            "Uses Tavily to perform deep web searches.  Retrieves, filters, "
            "and structures relevant information from multiple sources before "
            "passing a research brief to the Writer."
        ),
    },
    {
        "icon":  "✍️",
        "name":  "Writer Agent",
        "role":  "Content Drafting",
        "desc": (
            "Receives the research brief and crafts a well-structured, "
            "comprehensive response.  Adapts tone and format based on query "
            "type (blog post, summary, comparison, etc.)."
        ),
    },
    {
        "icon":  "📝",
        "name":  "Editor Agent",
        "role":  "Quality Assurance",
        "desc": (
            "Reviews the draft for factual accuracy, clarity, grammar, and "
            "completeness.  Provides the final, polished output returned to "
            "the user."
        ),
    },
]


# ── Public renderer ───────────────────────────────────────────────────────────

def render_about_page() -> None:
    """Render the About page. Call from app.py."""

    if st.button("← Back to Chat", key="about_back"):
        st.session_state.current_page = "chat"
        st.rerun()

    st.markdown("## 🤖 About AI Research Assistant")
    st.caption("Multi-Agent Research System powered by LangGraph")
    st.divider()

    # ── Overview ──────────────────────────────────────────────────────────────
    st.markdown("### 🎯 What is this?")
    st.markdown(
        """
        The **AI Research Assistant** is a production-grade, multi-agent system
        that breaks down complex research queries into a coordinated pipeline of
        specialised AI agents.

        Instead of a single LLM attempting everything, three agents collaborate:
        one **searches** the web, one **writes** the answer, and one **edits**
        the result — giving you well-sourced, polished responses every time.
        """
    )

    # ── Architecture ──────────────────────────────────────────────────────────
    st.markdown("### 🏗️ Architecture")
    st.markdown(
        """
        ```
        User Query
            │
            ▼
        ┌─────────────────────────────────────────┐
        │          LangGraph Supervisor            │
        └──────────────────┬──────────────────────┘
                           │
           ┌───────────────┼───────────────┐
           ▼               ▼               ▼
        ┌──────────┐  ┌──────────┐  ┌──────────┐
        │Researcher│→ │  Writer  │→ │  Editor  │
        │  Agent   │  │  Agent   │  │  Agent   │
        └──────────┘  └──────────┘  └──────────┘
               │            │             │
           Tavily         GPT-4o        GPT-4o
           Search         Draft         Review
                           │
                           ▼
                    Final Response
        ```
        """
    )

    # ── Agent cards ───────────────────────────────────────────────────────────
    st.markdown("### 🤝 Meet the Agents")
    for agent in _AGENTS_INFO:
        with st.container(border=True):
            col_icon, col_info = st.columns([1, 8])
            with col_icon:
                st.markdown(
                    f"<div style='font-size:32px;text-align:center;padding-top:6px;'>"
                    f"{agent['icon']}</div>",
                    unsafe_allow_html=True,
                )
            with col_info:
                st.markdown(f"**{agent['name']}** · *{agent['role']}*")
                st.caption(agent["desc"])

    # ── Tech stack ────────────────────────────────────────────────────────────
    st.markdown("### 🛠️ Technology Stack")
    cols = st.columns(4)
    for i, tech in enumerate(_TECH_STACK):
        with cols[i % 4]:
            st.markdown(
                f"""
                <div style="text-align:center;padding:0.75rem 0.5rem;
                            border:1px solid rgba(128,128,128,0.15);
                            border-radius:10px;margin-bottom:0.5rem;">
                    <div style="font-size:24px;">{tech['icon']}</div>
                    <div style="font-size:13px;font-weight:600;">{tech['name']}</div>
                    <div style="font-size:11px;opacity:0.5;">{tech['desc']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # ── Version info ──────────────────────────────────────────────────────────
    st.divider()
    st.markdown("### 📦 Build Info")
    col1, col2, col3 = st.columns(3)
    col1.metric("Version",   "1.0.0")
    col2.metric("Framework", "Streamlit 1.46")
    col3.metric("Python",    "3.11+")

    st.caption(
        "Frontend is fully decoupled from backend logic.  "
        "Connect your LangGraph pipeline in `agents/` to activate the AI features."
    )
