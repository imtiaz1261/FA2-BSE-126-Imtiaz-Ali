"""
Premium Chat UI — ChatGPT-quality interface.
Streaming, Markdown, tool-call steps, citations, copy actions, typing indicator.
"""
from __future__ import annotations
from typing import Generator
import streamlit as st
from api_client.client import api_client
from ui_components import (
    tool_step_card, tool_badge, source_card, section_header,
    security_blocked_banner, quota_exceeded_banner, toast_info,
)

_RAG_MODE   = "Knowledge (RAG)"
_AGENT_MODE = "Agent"
_RES_MODE   = "Research"

_CHAT_CSS = """
<style>
.mode-banner {
    display: flex; align-items: center; gap: 10px;
    background: rgba(79,142,247,0.06);
    border: 1px solid rgba(79,142,247,0.15);
    border-radius: 12px; padding: 10px 16px; margin-bottom: 16px;
    animation: fadeIn 0.3s ease;
}
.mode-icon { font-size: 1.2rem; }
.mode-label { color: #f0f4ff; font-weight: 600; font-size: 0.9rem; }
.mode-desc  { color: #64748b; font-size: 0.80rem; }

.msg-actions {
    display: flex; gap: 6px; margin-top: 6px;
    opacity: 0; transition: opacity 0.2s ease;
}
[data-testid="stChatMessage"]:hover .msg-actions { opacity: 1; }
.msg-action-btn {
    background: transparent; border: 1px solid #1e2d47;
    color: #4a5568; border-radius: 6px; padding: 3px 8px;
    font-size: 0.72rem; cursor: pointer; transition: all 0.15s ease;
}
.msg-action-btn:hover { background: #1e2d47; color: #94a3b8; }

.citation-card {
    background: #0f1629; border: 1px solid #1e2d47;
    border-left: 3px solid #8b5cf6;
    border-radius: 0 10px 10px 0; padding: 10px 14px;
    margin: 4px 0;
}
.citation-ref   { color: #8b5cf6; font-weight: 700; font-size: 0.82rem; }
.citation-name  { color: #94a3b8; font-size: 0.82rem; }
.citation-snip  { color: #4a5568; font-size: 0.78rem; margin-top:4px; }

.agent-thinking {
    display: flex; align-items: center; gap: 10px;
    color: #4a5568; font-size: 0.85rem; padding: 8px 0;
}
.thinking-dots { display: inline-flex; gap: 4px; }

.blocked-banner {
    background: rgba(239,68,68,0.08); border: 1px solid rgba(239,68,68,0.2);
    border-radius: 12px; padding: 16px 20px; margin: 8px 0;
    animation: fadeInUp 0.3s ease;
}
</style>
"""


# ── History ───────────────────────────────────────────────────────────────────

def _load_history(token: str, conversation_id: str) -> None:
    result = api_client.list_messages(token, conversation_id)
    st.session_state.setdefault("messages", {})
    if result.ok:
        st.session_state["messages"][conversation_id] = [
            {"role": m["role"], "content": m["content"]} for m in result.data
        ]
    else:
        st.session_state["messages"][conversation_id] = []


def _render_message(role: str, content: str) -> None:
    """Render a single chat bubble with copy helper."""
    with st.chat_message(role):
        st.markdown(content)
        # Copy hint (best we can do in Streamlit)
        if role == "assistant" and len(content) > 60:
            st.markdown(
                '<div class="msg-actions">'
                '<span class="msg-action-btn" title="Displayed above">📋 Copy</span>'
                '</div>',
                unsafe_allow_html=True,
            )


# ── Plain stream ──────────────────────────────────────────────────────────────

def _consume_stream(token, conv_id, prompt, mode, sink):
    for kind, payload in api_client.stream_message(token, conv_id, prompt, mode):
        if kind == "__error__":
            sink["error"] = payload
            return
        sink["full_text"] += payload
        yield payload


# ── RAG stream ────────────────────────────────────────────────────────────────

def _consume_rag_stream(token, conv_id, prompt, sink):
    for kind, payload in api_client.stream_message_with_citations(
        token, conv_id, prompt, _RAG_MODE
    ):
        if kind == "__error__":
            sink["error"] = payload
            return
        elif kind == "citations":
            sink["citations"] = payload
        elif kind == "chunk":
            sink["full_text"] += payload
            yield payload


# ── Agent stream ──────────────────────────────────────────────────────────────

_TOOL_ICONS = {
    "calculator": "🧮", "web_search": "🌐",
    "document_search": "📄", "get_current_datetime": "🕐",
    "add_days": "📅", "days_between": "📅", "day_of_week": "📅",
}


def _stream_agent(token, conv_id, prompt, sink):
    steps: list[dict] = []
    current_call: dict = {}
    status_ph = st.empty()

    for kind, payload in api_client.stream_agent(token, conv_id, prompt):
        if kind == "__error__":
            sink["error"] = payload
            status_ph.empty()
            return

        elif kind == "intent":
            lbl = {
                "tools":   "🔍 Planning which tools to use…",
                "direct":  "💬 Answering directly…",
                "clarify": "❓ Clarifying request…",
            }.get(payload, f"Thinking…")
            status_ph.markdown(
                f'<div class="agent-thinking">'
                f'<div class="thinking-dots">'
                f'<span class="typing-dot"></span>'
                f'<span class="typing-dot"></span>'
                f'<span class="typing-dot"></span>'
                f'</div>{lbl}</div>',
                unsafe_allow_html=True,
            )

        elif kind == "tool_call":
            name = payload.get("name", "tool")
            icon = _TOOL_ICONS.get(name, "🔧")
            status_ph.markdown(
                f'<div class="agent-thinking">'
                f'{icon} Running <strong style="color:#f0f4ff">{name}</strong>…'
                f'</div>',
                unsafe_allow_html=True,
            )
            current_call = {"name": name, "arguments": payload.get("arguments", {})}

        elif kind == "tool_result":
            name   = payload.get("name", "tool")
            result = payload.get("result", "")
            steps.append({
                "name":      current_call.get("name", name),
                "arguments": current_call.get("arguments", {}),
                "result":    result,
            })
            current_call = {}
            status_ph.markdown(
                f'<div class="agent-thinking" style="color:#22c55e;">✓ {name} completed</div>',
                unsafe_allow_html=True,
            )

        elif kind == "final":
            status_ph.empty()
            sink["steps"]     = steps
            sink["full_text"] = payload
            words = payload.split(" ")
            for i, word in enumerate(words):
                yield word + (" " if i < len(words) - 1 else "")

        elif kind == "chunk":
            sink["full_text"] += payload
            yield payload

    status_ph.empty()
    if "steps" not in sink:
        sink["steps"] = steps


# ── Citations panel ───────────────────────────────────────────────────────────

def _render_citations(citations: list[dict]) -> None:
    if not citations:
        return
    with st.expander(
        f"📚  **{len(citations)} source{'s' if len(citations)>1 else ''} cited**",
        expanded=False,
    ):
        for c in citations:
            page_str  = f"  ·  p.{c['page_number']}" if c.get("page_number") else ""
            score_str = f"  ·  {c.get('score',0):.0%} relevance"
            st.markdown(
                f'<div class="citation-card">'
                f'<span class="citation-ref">{c["ref"]}</span>'
                f'<span class="citation-name">  {c["document_name"]}{page_str}{score_str}</span>'
                f'<div class="citation-snip">{c.get("snippet","")[:180]}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )


# ── Agent steps panel ─────────────────────────────────────────────────────────

def _render_agent_steps(steps: list[dict]) -> None:
    if not steps:
        return
    tool_badges = " ".join(
        tool_badge(s.get("name", "tool")) for s in steps
    )
    with st.expander(
        f"🔧  **{len(steps)} tool call{'s' if len(steps)>1 else ''} made**",
        expanded=False,
    ):
        st.markdown(tool_badges, unsafe_allow_html=True)
        st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)
        for i, step in enumerate(steps, 1):
            tool_step_card(step, i)


# ── Mode banner ───────────────────────────────────────────────────────────────

_MODE_META = {
    _RAG_MODE:   ("📚", "#8b5cf6",
                  "Answers grounded in your documents · Citations shown below each reply"),
    _AGENT_MODE: ("🤖", "#10b981",
                  "AI agent with tools: calculator, web search, documents, date/time"),
}


def _render_mode_banner(mode: str) -> None:
    if mode not in _MODE_META:
        return
    icon, col, desc = _MODE_META[mode]
    st.markdown(
        f'<div class="mode-banner" style="border-color:{col}33;background:{col}08;">'
        f'<span class="mode-icon">{icon}</span>'
        f'<div><div class="mode-label">{mode}</div>'
        f'<div class="mode-desc">{desc}</div></div>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ── RAG hint ──────────────────────────────────────────────────────────────────

def _render_rag_hint(token: str) -> None:
    result = api_client.list_documents(token)
    if not result.ok:
        return
    docs      = result.data or []
    ready     = [d for d in docs if d.get("status") == "ready"]
    pending   = [d for d in docs if d.get("status") in ("processing","uploaded")]
    if not docs:
        toast_info("Upload documents via **Knowledge Base** in the sidebar to enable RAG mode.")
    elif not ready and pending:
        st.markdown(
            f'<div style="background:rgba(245,158,11,0.08);border:1px solid rgba(245,158,11,0.2);'
            f'border-radius:10px;padding:10px 14px;color:#f59e0b;font-size:0.84rem;">'
            f'⏳ {len(pending)} document(s) still indexing…</div>',
            unsafe_allow_html=True,
        )


# ── Main render ───────────────────────────────────────────────────────────────

def render_chat(conversation_id: str, mode: str) -> None:
    token = st.session_state["access_token"]
    st.markdown(_CHAT_CSS, unsafe_allow_html=True)

    # Load history
    if conversation_id not in st.session_state.get("messages", {}):
        _load_history(token, conversation_id)

    # Mode banner
    _render_mode_banner(mode)
    if mode == _RAG_MODE:
        _render_rag_hint(token)

    # Render message history
    for msg in st.session_state["messages"].get(conversation_id, []):
        _render_message(msg["role"], msg["content"])

    # Chat input
    prompt = st.chat_input(
        "Message the assistant…" if mode == "Chat" else
        "Ask about your documents…" if mode == _RAG_MODE else
        "Ask anything — I'll use tools…"
    )
    if not prompt:
        return

    # User turn
    st.session_state["messages"][conversation_id].append(
        {"role": "user", "content": prompt}
    )
    _render_message("user", prompt)

    sink = {"full_text": "", "error": None, "citations": [], "steps": []}

    with st.chat_message("assistant"):
        if mode == _AGENT_MODE:
            st.write_stream(_stream_agent(token, conversation_id, prompt, sink))
        elif mode == _RAG_MODE:
            st.write_stream(_consume_rag_stream(token, conversation_id, prompt, sink))
        else:
            st.write_stream(_consume_stream(token, conversation_id, prompt, mode, sink))

    # Error handling
    if sink["error"]:
        err = sink["error"]
        if isinstance(err, dict) and err.get("blocked"):
            security_blocked_banner(err.get("category","unknown"), err.get("reason",""))
        elif "429" in str(err) or "limit" in str(err).lower():
            udata = st.session_state.get("usage_data", {})
            quota_exceeded_banner(
                udata.get("monthly_used", 0),
                udata.get("monthly_limit", 100),
                udata.get("plan", "free"),
            )
        else:
            st.error(f"Error: {err}")
        return

    # Persist
    if sink["full_text"]:
        st.session_state["messages"][conversation_id].append(
            {"role": "assistant", "content": sink["full_text"]}
        )

    # Post-reply panels
    if mode == _AGENT_MODE and sink.get("steps"):
        _render_agent_steps(sink["steps"])
    if mode == _RAG_MODE and sink.get("citations"):
        _render_citations(sink["citations"])
