"""
components/info_panel.py
------------------------
Optional collapsible right-side information panel.

Shows:
  - Current workflow / active page
  - Active agent name
  - Processing status
  - Execution time
  - Conversation statistics (message count, estimated tokens)
  - Sources (placeholder list)
  - Token usage (placeholder progress bars)
"""

from __future__ import annotations

from datetime import datetime

import streamlit as st

from utils.formatters import conversation_stats, estimate_tokens, format_duration
from utils.session import get_active_messages, get_active_conversation, get_setting


# ──────────────────────────────────────────────────────────────────────────────
# Placeholder data (replace with real backend data)
# ──────────────────────────────────────────────────────────────────────────────

_PLACEHOLDER_SOURCES: list[dict] = [
    {"title": "Attention Is All You Need", "url": "#", "relevance": 0.97},
    {"title": "LangGraph Documentation",   "url": "#", "relevance": 0.91},
    {"title": "RAG Survey 2024",           "url": "#", "relevance": 0.85},
]

_MAX_CONTEXT_TOKENS = 8192  # placeholder context window size


# ──────────────────────────────────────────────────────────────────────────────
# Public renderer
# ──────────────────────────────────────────────────────────────────────────────

def render_info_panel() -> None:
    """
    Render the information panel inside a Streamlit expander.
    Call from app.py in the right column when show_info_panel is True.
    """
    with st.expander("ℹ️  Session Info", expanded=True):
        _render_workflow_section()
        st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
        _render_agent_section()
        st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
        _render_stats_section()
        st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
        _render_sources_section()
        st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
        _render_token_usage_section()


# ──────────────────────────────────────────────────────────────────────────────
# Section renderers
# ──────────────────────────────────────────────────────────────────────────────

def _render_workflow_section() -> None:
    """Show current page / workflow."""
    page    = st.session_state.get("current_page", "chat").capitalize()
    backend = get_setting("backend") or "offline"
    model   = get_setting("model") or "—"

    st.markdown(
        f"""
        <div class="info-panel">
            <div class="agent-panel-title">⚙️ Workflow</div>
            <div class="info-row">
                <span class="info-label">Page</span>
                <span class="info-value">{page}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Backend</span>
                <span class="info-value badge">{backend}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Model</span>
                <span class="info-value" style="font-size:0.75rem;">{model}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_agent_section() -> None:
    """Show active agent and processing status."""
    statuses: list[dict] = st.session_state.get("agent_statuses", [])
    is_generating: bool  = st.session_state.get("is_generating", False)
    exec_time: float     = st.session_state.get("last_exec_time", 0.0)

    # Find running agent (if any)
    active_agent = next(
        (a for a in statuses if a["status"] == "running"), None
    )
    active_name   = active_agent["name"] if active_agent else "—"
    overall_status = "Processing…" if is_generating else ("Done" if not is_generating else "Idle")
    exec_str = format_duration(exec_time) if exec_time else "—"

    st.markdown(
        f"""
        <div class="info-panel">
            <div class="agent-panel-title">🤖 Active Agent</div>
            <div class="info-row">
                <span class="info-label">Agent</span>
                <span class="info-value">{active_name}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Status</span>
                <span class="info-value">{"⚡ " + overall_status if is_generating else overall_status}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Last run</span>
                <span class="info-value">{exec_str}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_stats_section() -> None:
    """Show conversation-level statistics."""
    messages = get_active_messages()
    stats    = conversation_stats(messages)
    conv     = get_active_conversation()
    created  = conv["created"].strftime("%H:%M") if conv else "—"
    updated  = conv["updated"].strftime("%H:%M") if conv else "—"

    st.markdown(
        f"""
        <div class="info-panel">
            <div class="agent-panel-title">📊 Conversation Stats</div>
            <div class="info-row">
                <span class="info-label">Messages</span>
                <span class="info-value">{stats["total_messages"]}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Your messages</span>
                <span class="info-value">{stats["user_messages"]}</span>
            </div>
            <div class="info-row">
                <span class="info-label">AI responses</span>
                <span class="info-value">{stats["assistant_messages"]}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Est. tokens</span>
                <span class="info-value">{stats["estimated_tokens"]:,}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Started</span>
                <span class="info-value">{created}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Last activity</span>
                <span class="info-value">{updated}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_sources_section() -> None:
    """Render placeholder source citations."""
    messages = get_active_messages()
    sources  = _PLACEHOLDER_SOURCES if messages else []

    st.markdown(
        '<div class="agent-panel-title" style="margin-bottom:6px;">📚 Sources</div>',
        unsafe_allow_html=True,
    )

    if not sources:
        st.markdown(
            '<p style="font-size:0.78rem;color:var(--text-secondary);">'
            "No sources yet. Send a message to see retrieved references.</p>",
            unsafe_allow_html=True,
        )
        return

    for src in sources:
        relevance_pct = int(src["relevance"] * 100)
        bar_color     = "#10a37f" if src["relevance"] > 0.9 else "#6366f1"
        st.markdown(
            f"""
            <div style="padding:7px 0;border-bottom:1px solid var(--border-color);">
                <a href="{src['url']}" style="font-size:0.82rem;color:var(--accent);
                          text-decoration:none;font-weight:500;">
                    🔗 {src['title']}
                </a>
                <div style="display:flex;align-items:center;gap:6px;margin-top:4px;">
                    <div style="flex:1;height:4px;background:var(--border-color);
                                border-radius:2px;overflow:hidden;">
                        <div style="width:{relevance_pct}%;height:100%;
                                    background:{bar_color};border-radius:2px;">
                        </div>
                    </div>
                    <span style="font-size:0.7rem;color:var(--text-secondary);
                                 white-space:nowrap;">{relevance_pct}%</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _render_token_usage_section() -> None:
    """Render placeholder token usage bars."""
    messages      = get_active_messages()
    stats         = conversation_stats(messages)
    used_tokens   = stats["estimated_tokens"]
    max_tokens    = _MAX_CONTEXT_TOKENS
    usage_pct     = min(int((used_tokens / max_tokens) * 100), 100)
    bar_color     = "#ef4444" if usage_pct > 80 else "#f59e0b" if usage_pct > 60 else "#10a37f"

    prompt_tokens     = int(used_tokens * 0.6)   # placeholder split
    completion_tokens = used_tokens - prompt_tokens

    st.markdown(
        f"""
        <div class="info-panel">
            <div class="agent-panel-title">🔢 Token Usage</div>
            <div class="info-row">
                <span class="info-label">Context used</span>
                <span class="info-value">{used_tokens:,} / {max_tokens:,}</span>
            </div>
            <div style="margin:6px 0 10px;">
                <div style="background:var(--border-color);border-radius:4px;
                            height:6px;overflow:hidden;">
                    <div style="width:{usage_pct}%;height:100%;
                                background:{bar_color};border-radius:4px;
                                transition:width 0.5s ease;">
                    </div>
                </div>
                <div style="font-size:0.7rem;color:var(--text-secondary);
                            text-align:right;margin-top:3px;">{usage_pct}%</div>
            </div>
            <div class="info-row">
                <span class="info-label">Prompt tokens</span>
                <span class="info-value">{prompt_tokens:,}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Completion</span>
                <span class="info-value">{completion_tokens:,}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
