"""
components/welcome_screen.py
-----------------------------
Empty-state welcome screen shown when no conversation is active or
when the active conversation has no messages.

Contents
--------
- App logo + heading + subtitle
- Feature highlight cards (3-column)
- Suggested prompt cards (2 × 3 grid)

Clicking a suggestion card writes the text into ``st.session_state.pending_input``
and creates a new conversation; the main app picks this up and pre-fills
the chat input on the next render.
"""

from __future__ import annotations

import streamlit as st

from utils.session import create_conversation


# ── Suggested prompts ─────────────────────────────────────────────────────────

SUGGESTED_PROMPTS: list[dict[str, str]] = [
    {
        "icon":  "🔬",
        "title": "Research a topic",
        "text":  "Research the latest advancements in Artificial Intelligence and summarize key findings.",
    },
    {
        "icon":  "🧠",
        "title": "Explain a concept",
        "text":  "Explain how LangGraph works and how it enables multi-agent AI workflows.",
    },
    {
        "icon":  "⚖️",
        "title": "Compare technologies",
        "text":  "Compare FastAPI vs Django for building production REST APIs.",
    },
    {
        "icon":  "✍️",
        "title": "Write technical content",
        "text":  "Write a technical blog post about the benefits of retrieval-augmented generation (RAG).",
    },
    {
        "icon":  "📄",
        "title": "Summarize a paper",
        "text":  "Summarize the key contributions of the 'Attention Is All You Need' transformer paper.",
    },
    {
        "icon":  "🗺️",
        "title": "Create a roadmap",
        "text":  "Create a learning roadmap for becoming a professional AI/ML Engineer in 2025.",
    },
]

# ── Feature highlights ────────────────────────────────────────────────────────

_FEATURES: list[dict[str, str]] = [
    {
        "icon":  "🔍",
        "title": "Deep Research",
        "body":  "Researcher agent searches the web and retrieves up-to-date information from multiple sources.",
    },
    {
        "icon":  "✍️",
        "title": "Smart Writing",
        "body":  "Writer agent crafts well-structured, coherent responses tailored to your query.",
    },
    {
        "icon":  "📝",
        "title": "Quality Editing",
        "body":  "Editor agent reviews and refines the draft for accuracy, clarity, and completeness.",
    },
]


# ── Internal helpers ──────────────────────────────────────────────────────────

def _handle_suggestion(text: str) -> None:
    """Activate a suggestion: create/ensure conversation and pre-fill input."""
    if st.session_state.get("active_conversation_id") is None:
        create_conversation("New Chat")
    st.session_state.pending_input = text
    st.session_state.current_page = "chat"
    st.rerun()


# ── Public renderer ───────────────────────────────────────────────────────────

def render_welcome_screen() -> None:
    """
    Render the full welcome/empty-state screen.

    Call from ``app.py`` when ``get_active_messages()`` is empty.
    """
    # ── Hero section ──────────────────────────────────────────────────────────
    st.markdown(
        """
        <div class="welcome-wrapper">
            <div class="welcome-logo">🤖</div>
            <div class="welcome-title">AI Research Assistant</div>
            <div class="welcome-subtitle">
                A multi-agent system powered by LangGraph that researches, writes,
                and edits — so you get polished, well-sourced answers every time.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Feature cards ─────────────────────────────────────────────────────────
    feat_cols = st.columns(3, gap="medium")
    for col, feat in zip(feat_cols, _FEATURES):
        with col:
            st.markdown(
                f"""
                <div style="background:var(--bg-card,#fff);
                            border:1px solid rgba(128,128,128,0.15);
                            border-radius:14px;padding:1.25rem 1rem;
                            text-align:center;height:100%;
                            box-shadow:0 1px 6px rgba(0,0,0,0.06);">
                    <div style="font-size:28px;margin-bottom:0.5rem;">{feat['icon']}</div>
                    <div style="font-size:14px;font-weight:700;margin-bottom:0.4rem;">
                        {feat['title']}
                    </div>
                    <div style="font-size:12px;opacity:0.6;line-height:1.5;">
                        {feat['body']}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Suggested prompts heading ─────────────────────────────────────────────
    st.markdown(
        "<p style='text-align:center;font-size:13px;font-weight:600;"
        "opacity:0.55;letter-spacing:0.05em;text-transform:uppercase;"
        "margin-bottom:0.75rem;'>Try asking…</p>",
        unsafe_allow_html=True,
    )

    # ── 2-column suggestion grid ──────────────────────────────────────────────
    col_a, col_b = st.columns(2, gap="medium")
    for i, prompt in enumerate(SUGGESTED_PROMPTS):
        col = col_a if i % 2 == 0 else col_b
        with col:
            # Button label = icon + title
            btn_label = f"{prompt['icon']}  {prompt['title']}"
            if st.button(
                btn_label,
                key=f"suggestion_{i}",
                use_container_width=True,
                help=prompt["text"],
            ):
                _handle_suggestion(prompt["text"])

            # Preview text under the button
            st.markdown(
                f"<p style='font-size:11px;opacity:0.45;margin:-0.5rem 0 0.6rem;"
                f"padding-left:4px;'>{prompt['text'][:72]}…</p>",
                unsafe_allow_html=True,
            )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Quick-start CTA ───────────────────────────────────────────────────────
    st.markdown(
        "<p style='text-align:center;font-size:13px;opacity:0.45;'>"
        "Or type your own question in the input box below ↓</p>",
        unsafe_allow_html=True,
    )
