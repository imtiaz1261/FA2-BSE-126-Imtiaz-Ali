"""
utils/session.py
----------------
Centralised Streamlit session-state helpers.

All mutable app state lives here so every component imports from one place
instead of touching st.session_state directly.

Data model
~~~~~~~~~~
conversations : dict[str, Conversation]
    Key  → conversation id (uuid4 hex)
    Value → {
        "id":       str,
        "title":    str,
        "created":  datetime,
        "updated":  datetime,
        "messages": list[Message],
    }

active_conv_id : str | None   — currently open conversation
settings       : dict          — user preferences (model, theme, …)
agent_statuses : dict          — live agent-step states
show_info_panel: bool          — right panel visibility toggle
pending_input  : str           — pre-filled chat input (from prompt cards)
notification   : dict | None   — transient toast message
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

import streamlit as st

# ──────────────────────────────────────────────────────────────────────────────
# Type aliases (documentation only – Python doesn't enforce these at runtime)
# ──────────────────────────────────────────────────────────────────────────────
Message = dict[str, Any]          # role, content, timestamp, liked, …
Conversation = dict[str, Any]


# ──────────────────────────────────────────────────────────────────────────────
# Default values
# ──────────────────────────────────────────────────────────────────────────────

_DEFAULT_SETTINGS: dict[str, Any] = {
    "model":        "llama-3.1-8b-instant",
    "temperature":  0.7,
    "max_tokens":   2048,
    "streaming":    True,
    "dark_mode":    True,
    "font_size":    "Medium",
    "backend":      "offline",
}

_DEFAULT_AGENT_STATUSES: list[dict[str, str]] = [
    {"id": "researcher", "icon": "🔍", "name": "Researcher",  "status": "idle",  "detail": "Waiting…"},
    {"id": "writer",     "icon": "✍️",  "name": "Writer",      "status": "idle",  "detail": "Waiting…"},
    {"id": "editor",     "icon": "📝", "name": "Editor",      "status": "idle",  "detail": "Waiting…"},
]


# ──────────────────────────────────────────────────────────────────────────────
# Initialisation
# ──────────────────────────────────────────────────────────────────────────────

def init_session() -> None:
    """
    Call once at the top of app.py (inside every Streamlit rerun).
    Only sets keys that don't already exist so state survives reruns.
    """
    defaults: dict[str, Any] = {
        "conversations":    {},
        "active_conv_id":   None,
        "settings":         _DEFAULT_SETTINGS.copy(),
        "agent_statuses":   [s.copy() for s in _DEFAULT_AGENT_STATUSES],
        "show_info_panel":  False,
        "pending_input":    "",
        "notification":     None,
        "is_generating":    False,
        "current_page":     "chat",   # "chat" | "settings"
        "search_query":     "",
        "rename_conv_id":   None,     # conv being renamed
        "exec_start_time":  None,     # datetime when last generation started
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


# ──────────────────────────────────────────────────────────────────────────────
# Conversation helpers
# ──────────────────────────────────────────────────────────────────────────────

def new_conversation(title: str = "New Chat") -> str:
    """Create a fresh conversation, set it as active, and return its id."""
    conv_id = uuid.uuid4().hex
    now = datetime.now()
    st.session_state.conversations[conv_id] = {
        "id":       conv_id,
        "title":    title,
        "created":  now,
        "updated":  now,
        "messages": [],
    }
    st.session_state.active_conv_id = conv_id
    return conv_id


def get_active_conversation() -> Conversation | None:
    """Return the active conversation dict, or None if nothing is open."""
    cid = st.session_state.get("active_conv_id")
    if cid is None:
        return None
    return st.session_state.conversations.get(cid)


def get_active_messages() -> list[Message]:
    """Return the message list for the active conversation (empty list if none)."""
    conv = get_active_conversation()
    return conv["messages"] if conv else []


def switch_conversation(conv_id: str) -> None:
    """Switch the active conversation and reset transient state."""
    if conv_id in st.session_state.conversations:
        st.session_state.active_conv_id = conv_id
        st.session_state.is_generating = False
        reset_agent_statuses()


def rename_conversation(conv_id: str, new_title: str) -> None:
    """Rename a conversation by id."""
    if conv_id in st.session_state.conversations:
        st.session_state.conversations[conv_id]["title"] = new_title.strip() or "Untitled"
        st.session_state.conversations[conv_id]["updated"] = datetime.now()


def delete_conversation(conv_id: str) -> None:
    """Delete a conversation; switch active to latest remaining one."""
    convs = st.session_state.conversations
    convs.pop(conv_id, None)

    # If we deleted the active conv, point to the most-recent remaining one
    if st.session_state.active_conv_id == conv_id:
        if convs:
            latest = sorted(convs.values(), key=lambda c: c["updated"], reverse=True)[0]
            st.session_state.active_conv_id = latest["id"]
        else:
            st.session_state.active_conv_id = None


def clear_all_conversations() -> None:
    """Wipe every conversation and reset active id."""
    st.session_state.conversations = {}
    st.session_state.active_conv_id = None


def add_message(role: str, content: str, extra: dict[str, Any] | None = None) -> Message:
    """
    Append a message to the active conversation.

    Parameters
    ----------
    role    : "user" | "assistant"
    content : Markdown string
    extra   : optional metadata merged into the message dict

    Returns the created message dict.
    """
    conv = get_active_conversation()
    if conv is None:
        # Auto-create a conversation if none exists
        new_conversation()
        conv = get_active_conversation()

    msg: Message = {
        "id":        uuid.uuid4().hex,
        "role":      role,
        "content":   content,
        "timestamp": datetime.now(),
        "liked":     None,   # None | "up" | "down"
        "copied":    False,
        **(extra or {}),
    }
    conv["messages"].append(msg)
    conv["updated"] = datetime.now()

    # Auto-title from the first user message (first 50 chars)
    if role == "user" and conv["title"] == "New Chat" and len(conv["messages"]) == 1:
        conv["title"] = content[:50].strip() + ("…" if len(content) > 50 else "")

    return msg


def get_sorted_conversations() -> list[Conversation]:
    """Return all conversations sorted by last-updated descending."""
    return sorted(
        st.session_state.conversations.values(),
        key=lambda c: c["updated"],
        reverse=True,
    )


def search_conversations(query: str) -> list[Conversation]:
    """Filter conversations whose title or content contains *query* (case-insensitive)."""
    q = query.strip().lower()
    if not q:
        return get_sorted_conversations()
    results = []
    for conv in get_sorted_conversations():
        if q in conv["title"].lower():
            results.append(conv)
            continue
        for msg in conv["messages"]:
            if q in msg["content"].lower():
                results.append(conv)
                break
    return results


# ──────────────────────────────────────────────────────────────────────────────
# Agent status helpers
# ──────────────────────────────────────────────────────────────────────────────

def reset_agent_statuses() -> None:
    """Reset all agents back to idle."""
    st.session_state.agent_statuses = [s.copy() for s in _DEFAULT_AGENT_STATUSES]


def set_agent_status(agent_id: str, status: str, detail: str = "") -> None:
    """
    Update a single agent's status.

    Parameters
    ----------
    agent_id : "researcher" | "writer" | "editor"
    status   : "idle" | "running" | "done" | "error"
    detail   : short human-readable status string
    """
    for agent in st.session_state.agent_statuses:
        if agent["id"] == agent_id:
            agent["status"] = status
            agent["detail"] = detail
            break


def simulate_agent_progress(step: int) -> None:
    """
    Placeholder: advance agents through a fake pipeline based on step index.
    Replace with real backend events later.
    """
    reset_agent_statuses()
    if step >= 1:
        set_agent_status("researcher", "done",    "Research complete ✅")
    if step >= 2:
        set_agent_status("writer",     "done",    "Draft complete ✅")
    if step >= 3:
        set_agent_status("editor",     "done",    "Final response ready ✅")
    if step == 1:
        set_agent_status("researcher", "running", "Searching…")
    if step == 2:
        set_agent_status("writer",     "running", "Drafting…")
    if step == 3:
        set_agent_status("editor",     "running", "Reviewing…")


# ──────────────────────────────────────────────────────────────────────────────
# Settings helpers
# ──────────────────────────────────────────────────────────────────────────────

def get_setting(key: str) -> Any:
    """Read a single setting value."""
    return st.session_state.settings.get(key)


def update_setting(key: str, value: Any) -> None:
    """Write a single setting value."""
    st.session_state.settings[key] = value


# ──────────────────────────────────────────────────────────────────────────────
# Notification helpers
# ──────────────────────────────────────────────────────────────────────────────

def set_notification(message: str, kind: str = "success") -> None:
    """
    Queue a transient toast notification.

    Parameters
    ----------
    message : text to display
    kind    : "success" | "error" | "warn"
    """
    st.session_state.notification = {"message": message, "kind": kind}


def clear_notification() -> None:
    """Clear the current notification after it has been displayed."""
    st.session_state.notification = None


# ──────────────────────────────────────────────────────────────────────────────
# Misc helpers
# ──────────────────────────────────────────────────────────────────────────────

def set_pending_input(text: str) -> None:
    """Pre-fill the chat input (used by prompt cards)."""
    st.session_state.pending_input = text


def clear_pending_input() -> None:
    st.session_state.pending_input = ""


def toggle_info_panel() -> None:
    st.session_state.show_info_panel = not st.session_state.get("show_info_panel", False)


def set_page(page: str) -> None:
    """Navigate to a named page: 'chat' | 'settings'."""
    st.session_state.current_page = page
