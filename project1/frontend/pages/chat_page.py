"""
frontend/pages/chat_page.py — Claude-style Chat Interface
==========================================================
Uses the real SSE /chat/stream endpoint with proper frame parsing.
SSE frames: [CONV_ID], [DONE], [ERROR], [LIMIT], [BLOCKED], [REPLACE], or plain token
"""

import sys
from pathlib import Path
_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import streamlit as st
import requests
import json
from datetime import datetime
from backend.core.config import settings
from frontend.utils.session_state import get_auth_headers, add_message, clear_messages


# ── SSE streaming helper ─────────────────────────────────────────────────
def _stream_chat(user_message: str) -> str:
    """
    Call POST /api/v1/chat/stream with stream=True, parse SSE frames,
    update the placeholder in real-time, and return the full response text.
    """
    headers = get_auth_headers()
    headers["Accept"] = "text/event-stream"

    payload = {
        "message": user_message,
        "conversation_id": st.session_state.get("current_conversation_id"),
        "mode": "chat",
        "stream": True,
    }

    full_response = ""
    conv_id_received = None
    error_msg = None

    try:
        with requests.post(
            f"{settings.BACKEND_URL}/api/v1/chat/stream",
            headers=headers,
            json=payload,
            stream=True,
            timeout=90,
        ) as resp:
            if resp.status_code == 401:
                return "⚠️ Session expired. Please sign in again."
            if resp.status_code != 200:
                try:
                    detail = resp.json().get("detail", f"HTTP {resp.status_code}")
                except Exception:
                    detail = f"HTTP {resp.status_code}"
                return f"⚠️ {detail}"

            # parse SSE lines
            for raw_line in resp.iter_lines(decode_unicode=True):
                if not raw_line or not raw_line.startswith("data: "):
                    continue
                data = raw_line[6:]  # strip "data: "

                if data == "[DONE]":
                    break
                elif data.startswith("[CONV_ID]"):
                    conv_id_received = data[9:].strip()
                elif data.startswith("[ERROR]"):
                    error_msg = data[7:]
                    break
                elif data.startswith("[LIMIT]"):
                    error_msg = f"Usage limit reached: {data[7:]}"
                    break
                elif data.startswith("[BLOCKED]"):
                    error_msg = f"Request blocked: {data[9:]}"
                    break
                elif data.startswith("[REPLACE]"):
                    full_response = data[9:]
                else:
                    # plain token — unescape \n that SSE uses
                    full_response += data.replace("\\n", "\n")

    except requests.exceptions.Timeout:
        return "⚠️ Request timed out. The model may be busy — please try again."
    except requests.exceptions.ConnectionError:
        return "⚠️ Cannot connect to the backend. Is it running on port 8000?"
    except Exception as exc:
        return f"⚠️ Error: {exc}"

    if conv_id_received:
        st.session_state.current_conversation_id = conv_id_received

    if error_msg:
        return f"⚠️ {error_msg}"

    return full_response.strip() or "*(No response)*"


# ── conversation history ─────────────────────────────────────────────────
def _fetch_conversations() -> list:
    try:
        r = requests.get(
            f"{settings.BACKEND_URL}/api/v1/chat/conversations",
            headers=get_auth_headers(),
            timeout=8,
        )
        if r.status_code == 200:
            return r.json().get("conversations", [])
    except Exception:
        pass
    return []


def _load_conversation(conv_id: str) -> list:
    """Load messages for a conversation from the backend."""
    try:
        r = requests.get(
            f"{settings.BACKEND_URL}/api/v1/chat/conversations/{conv_id}",
            headers=get_auth_headers(),
            timeout=8,
        )
        if r.status_code == 200:
            return r.json().get("messages", [])
    except Exception:
        pass
    return []


# ── suggestion cards ─────────────────────────────────────────────────────
SUGGESTIONS = [
    ("🔬", "Explain quantum computing in simple terms"),
    ("💡", "Write a Python script to automate file renaming"),
    ("📊", "Analyze this data pattern and suggest insights"),
    ("🎨", "Design a REST API for a social media app"),
    ("✍️", "Help me write a professional email to a client"),
    ("🧮", "Explain the difference between SQL and NoSQL"),
]


# ── main render ──────────────────────────────────────────────────────────
def render_chat_page(page_type: str = "chat") -> None:
    if page_type == "history":
        _render_history()
        return

    messages: list = st.session_state.get("messages", [])

    # ── two-column layout: conversation panel + chat ─────────
    left_col, chat_col = st.columns([1, 4], gap="small")

    # ── LEFT: conversation list ──────────────────────────────
    with left_col:
        st.markdown("""
        <div style="padding:4px 0 10px">
          <span style="font-size:0.9375rem;font-weight:700;color:var(--text-primary)">
            💬 Chats
          </span>
        </div>""", unsafe_allow_html=True)

        if st.button("＋  New chat", use_container_width=True, key="btn_new_chat"):
            clear_messages()
            st.session_state.current_conversation_id = None
            st.rerun()

        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

        convs = _fetch_conversations()
        if convs:
            active_id = st.session_state.get("current_conversation_id")
            for c in convs[:25]:
                cid   = str(c.get("id", ""))
                title = (c.get("title") or "Untitled")[:32]
                is_active = active_id and str(active_id) == cid

                # style active conversation differently
                if is_active:
                    st.markdown(f"""
                    <div style="background:rgba(99,102,241,0.18);
                                border:1px solid rgba(99,102,241,0.3);
                                border-radius:8px;padding:8px 12px;
                                font-size:0.8125rem;font-weight:600;
                                color:#a5b4fc;margin:2px 0;
                                cursor:default">
                        ▶ {title}
                    </div>""", unsafe_allow_html=True)
                else:
                    if st.button(title, key=f"conv_{cid}", use_container_width=True):
                        st.session_state.current_conversation_id = cid
                        raw_msgs = _load_conversation(cid)
                        # convert backend format to session format
                        st.session_state.messages = [
                            {"role": m["role"], "content": m["content"],
                             "timestamp": str(m.get("created_at", ""))}
                            for m in raw_msgs
                        ]
                        st.rerun()
        else:
            st.markdown(
                '<p style="color:var(--text-muted);font-size:0.8rem;'
                'padding:8px 2px">No conversations yet</p>',
                unsafe_allow_html=True
            )

    # ── RIGHT: main chat area ────────────────────────────────
    with chat_col:
        if not messages:
            _render_welcome()
        else:
            _render_messages(messages)

        # ── thinking indicator ────────────────────────────────
        if st.session_state.get("_chat_thinking"):
            st.markdown("""
            <div style="display:flex;align-items:center;gap:8px;
                        padding:8px 14px;margin:6px 0;width:fit-content;
                        background:rgba(99,102,241,0.08);
                        border:1px solid rgba(99,102,241,0.2);
                        border-radius:10px">
                <div style="display:flex;gap:3px">
                  <span style="width:6px;height:6px;border-radius:50%;
                               background:#6366f1;display:inline-block;
                               animation:dot1 1.2s infinite"></span>
                  <span style="width:6px;height:6px;border-radius:50%;
                               background:#818cf8;display:inline-block;
                               animation:dot2 1.2s infinite"></span>
                  <span style="width:6px;height:6px;border-radius:50%;
                               background:#a5b4fc;display:inline-block;
                               animation:dot3 1.2s infinite"></span>
                </div>
                <span style="color:#a5b4fc;font-size:0.85rem;font-weight:500">
                    AIHub is thinking…
                </span>
            </div>
            <style>
            @keyframes dot1{0%,80%,100%{opacity:.2}40%{opacity:1}}
            @keyframes dot2{0%,80%,100%{opacity:.2}60%{opacity:1}}
            @keyframes dot3{0%,80%,100%{opacity:.2}80%{opacity:1}}
            </style>
            """, unsafe_allow_html=True)

        # ── Chat input ────────────────────────────────────────
        user_input = st.chat_input("Message AIHub…", key="main_chat_input")

        if user_input and user_input.strip():
            text = user_input.strip()
            # append user message immediately
            add_message("user", text)
            st.session_state["_chat_thinking"] = True
            st.rerun()

    # ── handle pending message after rerun ───────────────────
    if st.session_state.get("_chat_thinking"):
        messages = st.session_state.get("messages", [])
        # the last message is the user's — send it
        pending = next(
            (m["content"] for m in reversed(messages) if m["role"] == "user"),
            None
        )
        if pending:
            response = _stream_chat(pending)
            add_message("assistant", response)
        st.session_state["_chat_thinking"] = False
        st.rerun()


# ── welcome screen ───────────────────────────────────────────────────────
def _render_welcome() -> None:
    name = st.session_state.get("user_full_name") or \
           (st.session_state.get("user_email") or "there").split("@")[0]

    st.markdown(f"""
    <div style="text-align:center;padding:2.5rem 1rem 2rem">
        <div style="font-size:3rem;margin-bottom:0.75rem
                    ;filter:drop-shadow(0 0 20px rgba(99,102,241,0.5))">✨</div>
        <h1 style="font-size:1.875rem;font-weight:800;margin:0;
                   background:linear-gradient(135deg,#a5b4fc 0%,#67e8f9 60%,#a5b4fc 100%);
                   -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                   background-clip:text;letter-spacing:-0.03em">
            Good day, {name}
        </h1>
        <p style="color:var(--text-muted);font-size:0.9375rem;margin:0.625rem 0 0">
            How can AIHub help you today?
        </p>
    </div>
    """, unsafe_allow_html=True)

    # suggestion cards — 3 per row
    row1 = st.columns(3, gap="small")
    row2 = st.columns(3, gap="small")
    all_cols = row1 + row2

    for col, (icon, prompt) in zip(all_cols, SUGGESTIONS):
        with col:
            short = prompt[:35] + "…" if len(prompt) > 35 else prompt
            if st.button(
                f"{icon}\n\n{short}",
                key=f"sug_{hash(prompt)}",
                use_container_width=True,
            ):
                add_message("user", prompt)
                st.session_state["_chat_thinking"] = True
                st.rerun()


# ── message thread renderer ──────────────────────────────────────────────
def _fmt_time(ts: str) -> str:
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return dt.strftime("%-I:%M %p")
    except Exception:
        return ""


def _render_messages(messages: list) -> None:
    for msg in messages:
        role    = msg.get("role", "user")
        content = msg.get("content", "")
        ts      = _fmt_time(msg.get("timestamp", ""))

        if role == "user":
            # right-aligned bubble
            st.markdown(f"""
            <div style="display:flex;justify-content:flex-end;margin:8px 0">
                <div>
                    <div style="background:linear-gradient(135deg,#4f46e5,#6366f1);
                                color:white;padding:11px 16px;
                                border-radius:18px 18px 4px 18px;
                                max-width:540px;word-break:break-word;
                                font-size:0.9375rem;line-height:1.6;
                                box-shadow:0 4px 16px rgba(99,102,241,0.3)">
                        {content}
                    </div>
                    <div style="text-align:right;font-size:0.7rem;
                                color:var(--text-muted);margin-top:3px;
                                padding-right:4px">{ts}</div>
                </div>
            </div>""", unsafe_allow_html=True)

        elif role == "assistant":
            # left-aligned glass bubble with st.chat_message for markdown/code
            col_avatar, col_msg = st.columns([0.08, 0.92], gap="small")
            with col_avatar:
                st.markdown("""
                <div style="width:32px;height:32px;border-radius:50%;
                            background:linear-gradient(135deg,#6366f1,#06b6d4);
                            display:flex;align-items:center;justify-content:center;
                            font-size:0.875rem;margin-top:6px">🤖</div>
                """, unsafe_allow_html=True)
            with col_msg:
                st.markdown(f"""
                <div style="background:rgba(255,255,255,0.05);
                            border:1px solid rgba(255,255,255,0.09);
                            border-radius:4px 18px 18px 18px;
                            padding:12px 16px;max-width:660px;
                            word-break:break-word;
                            box-shadow:0 4px 16px rgba(0,0,0,0.2)">
                """, unsafe_allow_html=True)
                st.markdown(content)   # native markdown + code blocks
                if ts:
                    st.markdown(
                        f'<div style="font-size:0.7rem;color:var(--text-muted);'
                        f'margin-top:4px">{ts}</div>',
                        unsafe_allow_html=True
                    )
                st.markdown("</div>", unsafe_allow_html=True)

        elif role == "tool":
            st.markdown(f"""
            <div style="background:rgba(6,182,212,0.07);
                        border-left:3px solid #06b6d4;
                        border-radius:0 8px 8px 0;
                        padding:8px 14px;margin:4px 0;
                        font-family:'Fira Code',monospace;
                        font-size:0.8rem;color:#67e8f9">
                🔧 <strong>Tool</strong> &nbsp;{content}
            </div>""", unsafe_allow_html=True)


# ── history page ─────────────────────────────────────────────────────────
def _render_history() -> None:
    st.markdown("""
    <div class="page-header">
        <div class="page-title">📚 Conversation History</div>
        <div class="page-subtitle">All your past sessions with AIHub</div>
    </div>""", unsafe_allow_html=True)

    convs = _fetch_conversations()
    if not convs:
        st.markdown("""
        <div style="text-align:center;padding:4rem 1rem">
            <div style="font-size:3rem;margin-bottom:8px">🗂️</div>
            <p style="color:var(--text-muted)">
                No conversations yet. Start chatting to see your history here.
            </p>
        </div>""", unsafe_allow_html=True)
        return

    for c in convs:
        cid     = str(c.get("id", ""))
        title   = c.get("title") or "Untitled"
        msgs    = c.get("message_count", 0)
        tokens  = c.get("total_tokens", 0)
        feature = c.get("feature", "chat")
        updated = (c.get("updated_at") or "")[:10]
        feat_icon = {"chat": "💬", "rag": "🔍", "agent": "🤖"}.get(feature, "💬")

        col1, col2 = st.columns([5, 1])
        with col1:
            st.markdown(f"""
            <div class="glass-card" style="padding:14px 18px;margin:4px 0">
              <div style="display:flex;align-items:center;gap:14px">
                <div style="font-size:1.5rem">{feat_icon}</div>
                <div style="flex:1;min-width:0">
                  <div style="font-weight:600;color:var(--text-primary);
                              font-size:0.9375rem;white-space:nowrap;
                              overflow:hidden;text-overflow:ellipsis">{title}</div>
                  <div style="font-size:0.76rem;color:var(--text-muted);margin-top:3px">
                    {msgs} messages &nbsp;·&nbsp; {tokens:,} tokens &nbsp;·&nbsp; {updated}
                  </div>
                </div>
                <span class="badge badge-purple">{feature}</span>
              </div>
            </div>""", unsafe_allow_html=True)
        with col2:
            st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)
            if st.button("Open →", key=f"h_{cid}", use_container_width=True):
                st.session_state.current_conversation_id = cid
                raw = _load_conversation(cid)
                st.session_state.messages = [
                    {"role": m["role"], "content": m["content"],
                     "timestamp": str(m.get("created_at", ""))}
                    for m in raw
                ]
                st.session_state.page = "chat"
                st.rerun()
