"""
components/empty_state.py
-------------------------
Welcome / empty-state screen shown when no active conversation has messages.

Features:
  - App logo + welcome heading + tagline
  - Feature highlights
  - Suggested prompt cards (clicking pre-fills the chat input)
"""

from __future__ import annotations

import streamlit as st

from utils.session import new_conversation, set_pending_input


# ──────────────────────────────────────────────────────────────────────────────
# Prompt card definitions
# ──────────────────────────────────────────────────────────────────────────────

_PROMPT_CARDS: list[dict[str, str]] = [
    {
        "icon":  "🔬",
        "title": "Research AI",
        "desc":  "Explore the latest in artificial intelligence.",
        "prompt": "Research the latest advancements in artificial intelligence and summarise "
                  "the key breakthroughs from the past year.",
    },
    {
        "icon":  "🦜",
        "title": "Explain LangGraph",
        "desc":  "Understand multi-agent orchestration.",
        "prompt": "Explain LangGraph and how it enables multi-agent orchestration in AI systems. "
                  "Include a simple code example.",
    },
    {
        "icon":  "⚡",
        "title": "FastAPI vs Django",
        "desc":  "Compare two popular Python frameworks.",
        "prompt": "Compare FastAPI and Django for building REST APIs. Cover performance, "
                  "ease of use, ecosystem, and when to choose each.",
    },
    {
        "icon":  "✍️",
        "title": "Write a Tech Blog",
        "desc":  "Draft a professional technical article.",
        "prompt": "Write a professional technical blog post about the future of RAG "
                  "(Retrieval-Augmented Generation) in enterprise AI applications.",
    },
    {
        "icon":  "📄",
        "title": "Summarise Paper",
        "desc":  "Condense a research paper into key points.",
        "prompt": "Summarise the key contributions, methodology, and results of the "
                  "'Attention Is All You Need' transformer paper.",
    },
    {
        "icon":  "🧠",
        "title": "Explain RAG",
        "desc":  "How retrieval-augmented generation works.",
        "prompt": "Explain Retrieval-Augmented Generation (RAG) step by step, including "
                  "its components, benefits, and real-world use cases.",
    },
]

# ──────────────────────────────────────────────────────────────────────────────
# Feature highlight bullets
# ──────────────────────────────────────────────────────────────────────────────

_FEATURES: list[tuple[str, str]] = [
    ("🔍", "Deep-dive research with a Researcher agent"),
    ("✍️", "Polished content via a dedicated Writer agent"),
    ("📝", "Quality review by an Editor agent"),
    ("📊", "Source citations and token usage tracking"),
]


# ──────────────────────────────────────────────────────────────────────────────
# Public renderer
# ──────────────────────────────────────────────────────────────────────────────

def render_empty_state() -> None:
    """
    Render the full welcome / empty-state screen.
    Call this from app.py when the active conversation has no messages.
    """
    # Centre content with padding (replicate .welcome-screen layout via columns)
    _, centre, _ = st.columns([1, 6, 1])

    with centre:
        # Logo + heading
        st.markdown(
            """
            <div class="welcome-screen">
                <div class="welcome-logo">🤖</div>
                <h1 class="welcome-title">ResearchAI Assistant</h1>
                <p class="welcome-subtitle">
                    Your multi-agent research companion powered by LangGraph.<br>
                    Ask anything — I'll research, write, and refine the answer for you.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Feature highlights
        _render_features()

        st.markdown(
            '<p style="text-align:center;color:var(--text-secondary);'
            'font-size:0.85rem;margin:24px 0 12px;">— or try a suggestion —</p>',
            unsafe_allow_html=True,
        )

        # Prompt cards grid
        _render_prompt_cards()

        # Footer note
        st.markdown(
            '<p style="text-align:center;color:var(--text-secondary);'
            'font-size:0.75rem;margin-top:32px;">'
            "ResearchAI · Multi-Agent · Powered by LangGraph + RAG"
            "</p>",
            unsafe_allow_html=True,
        )


# ──────────────────────────────────────────────────────────────────────────────
# Private helpers
# ──────────────────────────────────────────────────────────────────────────────

def _render_features() -> None:
    """Render a 2-column feature list."""
    cols = st.columns(2)
    for i, (icon, text) in enumerate(_FEATURES):
        with cols[i % 2]:
            st.markdown(
                f"""
                <div style="display:flex;align-items:center;gap:10px;
                            padding:8px 12px;margin-bottom:8px;
                            background:var(--bg-card);
                            border:1px solid var(--border-color);
                            border-radius:var(--radius-sm);">
                    <span style="font-size:1.2rem;">{icon}</span>
                    <span style="font-size:0.85rem;color:var(--text-primary);">{text}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )


def _render_prompt_cards() -> None:
    """Render the 3-column grid of clickable prompt cards."""
    cols = st.columns(3)

    for idx, card in enumerate(_PROMPT_CARDS):
        with cols[idx % 3]:
            # Render the card face
            st.markdown(
                f"""
                <div class="prompt-card">
                    <div class="card-icon">{card["icon"]}</div>
                    <div class="card-title">{card["title"]}</div>
                    <div class="card-desc">{card["desc"]}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            # Invisible button overlaying the card to capture clicks
            if st.button(
                f"Try: {card['title']}",
                key=f"prompt_card_{idx}",
                use_container_width=True,
                help=card["prompt"],
            ):
                # Ensure a conversation is open before pre-filling input
                if st.session_state.get("active_conv_id") is None:
                    new_conversation()
                set_pending_input(card["prompt"])
                st.rerun()
