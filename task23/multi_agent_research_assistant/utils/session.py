"""
utils/session.py
----------------
Streamlit session-state initialisation and helper functions.

All mutable UI state lives in ``st.session_state``.  Calling
``init_session_state()`` once at app start guarantees every key exists
with a sensible default, avoiding KeyError sprinkled through components.

Data shapes
-----------
conversations : dict[str, Conversation]
    Keyed by a UUID string.

Conversation (TypedDict) ::
    {
        "id":         str,          # UUID
        "title":      str,          # editable display name
        "messages":   list[Message],
        "created_at": str,          # ISO timestamp
        "updated_at": str,
    }

Message (TypedDict) ::
    {
        "id":         str,          # UUID
        "role":       "user" | "assistant",
        "content":    str,
        "timestamp":  str,          # ISO timestamp
        "liked":      bool | None,  # None = no feedback yet
    }

AgentStatus ::
    {
        "researcher": "idle" | "running" | "done" | "error",
        "writer":     "idle" | "running" | "done" | "error",
        "editor":     "idle" | "running" | "done" | "error",
    }
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Literal, TypedDict

import streamlit as st


# ── Type aliases ─────────────────────────────────────────────────────────────

AgentState = Literal["idle", "running", "done", "error"]


class Message(TypedDict):
    id: str
    role: Literal["user", "assistant"]
    content: str
    timestamp: str
    liked: bool | None


class Conversation(TypedDict):
    id: str
    title: str
    messages: list[Message]
    created_at: str
    updated_at: str


# ── Defaults ──────────────────────────────────────────────────────────────────

_AGENT_STATUS_DEFAULT: dict[str, AgentState] = {
    "researcher": "idle",
    "writer":     "idle",
    "editor":     "idle",
}

_SETTINGS_DEFAULT: dict[str, Any] = {
    "model":         "gpt-4o-mini",
    "provider":      "openai",
    "temperature":   0.7,
    "max_tokens":    4096,
    "streaming":     True,
    "dark_mode":     False,
    "font_size":     "Medium",
    "show_info_panel": True,
    "show_agent_panel": True,
}

_WORKFLOW_INFO_DEFAULT: dict[str, Any] = {
    "active_agent":     "—",
    "status":           "Idle",
    "execution_time":   0.0,
    "sources":          [],
    "token_usage":      {"prompt": 0, "completion": 0, "total": 0},
}


# ── Initialisation ────────────────────────────────────────────────────────────

def init_session_state() -> None:
    """
    Ensure every required key exists in ``st.session_state``.

    Safe to call on every rerun — existing values are never overwritten.
    """
    defaults: dict[str, Any] = {
        # ── Conversation management ──────────────────────────────
        "conversations":        {},        # dict[id, Conversation]
        "active_conversation_id": None,    # str | None
        "search_query":         "",        # sidebar search filter

        # ── UI flags ─────────────────────────────────────────────
        "is_processing":        False,     # backend call in-flight
        "show_agent_panel":     True,
        "show_info_panel":      True,
        "current_page":         "chat",    # "chat" | "settings" | "about"

        # ── Input ─────────────────────────────────────────────────
        "pending_input":        "",        # populated by suggestion cards
        "input_key":            0,         # increment to clear textarea

        # ── Agent progress ────────────────────────────────────────
        "agent_status":         dict(_AGENT_STATUS_DEFAULT),
        "agent_log":            [],        # list[str] of log lines

        # ── Info panel ────────────────────────────────────────────
        "workflow_info":        dict(_WORKFLOW_INFO_DEFAULT),

        # ── Notifications ─────────────────────────────────────────
        "notification":         None,      # {"msg": str, "type": str} | None

        # ── Settings ──────────────────────────────────────────────
        "settings":             dict(_SETTINGS_DEFAULT),

        # ── Rename / delete UI state ──────────────────────────────
        "renaming_conv_id":     None,
        "deleting_conv_id":     None,

        # ── Streaming / regenerate ────────────────────────────────
        "last_user_query":      "",        # used by regenerate
        "streaming_response":   "",        # partial text while streaming
        "regenerate_trigger":   False,     # set True to redo last query
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


# ── Conversation helpers ──────────────────────────────────────────────────────

def _now() -> str:
    """Return current UTC time as an ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()


def create_conversation(title: str = "New Chat") -> str:
    """
    Create a new conversation, add it to session state, and activate it.

    Returns
    -------
    str
        The new conversation's UUID.
    """
    conv_id = str(uuid.uuid4())
    now = _now()
    st.session_state.conversations[conv_id] = Conversation(
        id=conv_id,
        title=title,
        messages=[],
        created_at=now,
        updated_at=now,
    )
    st.session_state.active_conversation_id = conv_id
    return conv_id


def get_active_conversation() -> Conversation | None:
    """Return the currently active conversation, or None."""
    cid = st.session_state.get("active_conversation_id")
    if cid is None:
        return None
    return st.session_state.conversations.get(cid)


def get_active_messages() -> list[Message]:
    """Return the message list for the active conversation (may be empty)."""
    conv = get_active_conversation()
    return conv["messages"] if conv else []


def add_message(role: Literal["user", "assistant"], content: str) -> Message:
    """
    Append a message to the active conversation and return it.

    Creates a new conversation automatically if none is active.
    """
    if st.session_state.active_conversation_id is None:
        create_conversation()

    msg: Message = {
        "id":        str(uuid.uuid4()),
        "role":      role,
        "content":   content,
        "timestamp": _now(),
        "liked":     None,
    }
    cid = st.session_state.active_conversation_id
    conv = st.session_state.conversations[cid]
    conv["messages"].append(msg)
    conv["updated_at"] = _now()

    # Auto-title the conversation from the first user message
    if role == "user" and len(conv["messages"]) == 1:
        conv["title"] = content[:48] + ("…" if len(content) > 48 else "")

    return msg


def rename_conversation(conv_id: str, new_title: str) -> None:
    """Rename an existing conversation."""
    if conv_id in st.session_state.conversations:
        st.session_state.conversations[conv_id]["title"] = new_title.strip() or "Untitled"
        st.session_state.conversations[conv_id]["updated_at"] = _now()


def delete_conversation(conv_id: str) -> None:
    """Delete a conversation and reset active id if it was selected."""
    st.session_state.conversations.pop(conv_id, None)
    if st.session_state.active_conversation_id == conv_id:
        remaining = list(st.session_state.conversations.keys())
        st.session_state.active_conversation_id = remaining[0] if remaining else None


def clear_active_chat() -> None:
    """Remove all messages from the active conversation."""
    conv = get_active_conversation()
    if conv:
        conv["messages"] = []
        conv["updated_at"] = _now()


def clear_all_conversations() -> None:
    """Delete every conversation and reset to a blank state."""
    st.session_state.conversations = {}
    st.session_state.active_conversation_id = None


def set_message_feedback(msg_id: str, liked: bool) -> None:
    """Record like / dislike on a specific message."""
    conv = get_active_conversation()
    if conv is None:
        return
    for msg in conv["messages"]:
        if msg["id"] == msg_id:
            # Toggle off if same value clicked again
            msg["liked"] = None if msg["liked"] == liked else liked
            break


# ── Agent-status helpers ──────────────────────────────────────────────────────

def reset_agent_status() -> None:
    """Reset all agent statuses to idle."""
    st.session_state.agent_status = dict(_AGENT_STATUS_DEFAULT)
    st.session_state.agent_log = []


def set_agent_status(agent: str, state: AgentState) -> None:
    """Update a single agent's status."""
    st.session_state.agent_status[agent] = state


# ── Settings helpers ──────────────────────────────────────────────────────────

def get_setting(key: str) -> Any:
    """Return a setting value, falling back to the default."""
    return st.session_state.settings.get(key, _SETTINGS_DEFAULT.get(key))


def update_setting(key: str, value: Any) -> None:
    """Persist a setting change into session state."""
    st.session_state.settings[key] = value


def is_dark_mode() -> bool:
    """Convenience accessor for the dark-mode flag."""
    return bool(get_setting("dark_mode"))


# ── Notification helpers ──────────────────────────────────────────────────────

def show_notification(msg: str, kind: Literal["success", "error", "info"] = "info") -> None:
    """Queue a toast notification to be displayed on the next render."""
    st.session_state.notification = {"msg": msg, "type": kind}


def clear_notification() -> None:
    """Dismiss any queued notification."""
    st.session_state.notification = None


# ── Workflow info helpers ─────────────────────────────────────────────────────

def update_workflow_info(**kwargs: Any) -> None:
    """Merge keyword arguments into the workflow info dict."""
    st.session_state.workflow_info.update(kwargs)


def reset_workflow_info() -> None:
    """Reset workflow info to defaults."""
    st.session_state.workflow_info = dict(_WORKFLOW_INFO_DEFAULT)


# ── Regenerate helpers ────────────────────────────────────────────────────────

def set_last_user_query(query: str) -> None:
    """Store the most recent user query so Regenerate can replay it."""
    st.session_state.last_user_query = query


def get_last_user_query() -> str:
    """Return the last stored user query, or empty string."""
    return st.session_state.get("last_user_query", "")


def pop_regenerate_trigger() -> bool:
    """
    Return True (and reset the flag) if a regenerate was requested.
    Removes the last assistant message so the response can be replaced.
    """
    if not st.session_state.get("regenerate_trigger", False):
        return False
    st.session_state.regenerate_trigger = False

    # Drop the last assistant message so it gets replaced
    conv = get_active_conversation()
    if conv and conv["messages"] and conv["messages"][-1]["role"] == "assistant":
        conv["messages"].pop()

    return True
