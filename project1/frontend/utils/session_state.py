"""
frontend/utils/session_state.py — Streamlit Session State Management
====================================================================
Centralized initialization and management of Streamlit session_state.
This ensures consistent state across page reloads and navigation.
"""

import streamlit as st
from datetime import datetime, timedelta
from typing import Optional


def init_session_state() -> None:
    """
    Initialize all required session state variables.
    
    Called once on app startup. Streamlit reruns the app on every user
    interaction, but session_state persists across reruns — this ensures
    all keys exist before any component tries to access them.
    
    Keys initialized:
    - Authentication: user_id, token, is_authenticated, user_email, user_role
    - UI State: page, sidebar_collapsed, theme
    - Chat: current_conversation_id, messages, agent_status
    - Data: subscription_info, usage_metrics, documents
    """
    
    # ===================================================================
    # Authentication State
    # ===================================================================
    if "user_id" not in st.session_state:
        st.session_state.user_id = None
    
    if "token" not in st.session_state:
        st.session_state.token = None
    
    if "is_authenticated" not in st.session_state:
        st.session_state.is_authenticated = False
    
    if "user_email" not in st.session_state:
        st.session_state.user_email = None
    
    if "user_role" not in st.session_state:
        st.session_state.user_role = "user"  # "user" | "admin"
    
    if "user_full_name" not in st.session_state:
        st.session_state.user_full_name = None
    
    # ===================================================================
    # UI Navigation & Theme
    # ===================================================================
    if "page" not in st.session_state:
        st.session_state.page = "chat"
    
    if "sidebar_collapsed" not in st.session_state:
        st.session_state.sidebar_collapsed = False
    
    if "theme" not in st.session_state:
        st.session_state.theme = "dark"  # "dark" | "light"
    
    # ===================================================================
    # Chat & Conversation State
    # ===================================================================
    if "current_conversation_id" not in st.session_state:
        st.session_state.current_conversation_id = None
    
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    if "agent_status" not in st.session_state:
        st.session_state.agent_status = "idle"  # "idle" | "processing" | "error"
    
    if "agent_error_message" not in st.session_state:
        st.session_state.agent_error_message = None
    
    if "last_agent_response_at" not in st.session_state:
        st.session_state.last_agent_response_at = None
    
    if "show_agent_logs" not in st.session_state:
        st.session_state.show_agent_logs = False
    
    # ===================================================================
    # Subscription & Usage State
    # ===================================================================
    if "subscription_tier" not in st.session_state:
        st.session_state.subscription_tier = "free"  # "free" | "pro" | "enterprise"
    
    if "subscription_renews_at" not in st.session_state:
        st.session_state.subscription_renews_at = None
    
    if "usage_tokens_this_month" not in st.session_state:
        st.session_state.usage_tokens_this_month = 0
    
    if "usage_tokens_limit" not in st.session_state:
        st.session_state.usage_tokens_limit = 50_000  # Free tier default
    
    if "usage_requests_today" not in st.session_state:
        st.session_state.usage_requests_today = 0
    
    if "usage_requests_limit" not in st.session_state:
        st.session_state.usage_requests_limit = 20  # Free tier default
    
    # ===================================================================
    # Documents & Files State
    # ===================================================================
    if "documents" not in st.session_state:
        st.session_state.documents = []
    
    if "uploaded_file_status" not in st.session_state:
        st.session_state.uploaded_file_status = None
    
    if "vector_store_synced" not in st.session_state:
        st.session_state.vector_store_synced = False
    
    # ===================================================================
    # Admin Panel State
    # ===================================================================
    if "admin_users_filter" not in st.session_state:
        st.session_state.admin_users_filter = "all"  # "all" | "active" | "admin"
    
    if "admin_users_list" not in st.session_state:
        st.session_state.admin_users_list = []
    
    if "admin_recent_activity" not in st.session_state:
        st.session_state.admin_recent_activity = []
    
    if "admin_system_stats" not in st.session_state:
        st.session_state.admin_system_stats = {}
    
    # ===================================================================
    # Modal/Dialog State
    # ===================================================================
    if "show_settings_modal" not in st.session_state:
        st.session_state.show_settings_modal = False
    
    if "show_subscription_modal" not in st.session_state:
        st.session_state.show_subscription_modal = False
    
    if "show_confirmation_dialog" not in st.session_state:
        st.session_state.show_confirmation_dialog = False
    
    if "confirmation_message" not in st.session_state:
        st.session_state.confirmation_message = None
    
    if "confirmation_action" not in st.session_state:
        st.session_state.confirmation_action = None


def is_authenticated() -> bool:
    """
    Check if the current user is authenticated.
    
    Returns:
        True if user_id and token both exist in session state, False otherwise.
    """
    return (
        st.session_state.get("user_id") is not None
        and st.session_state.get("token") is not None
        and st.session_state.get("is_authenticated", False)
    )


def login_user(
    user_id: str,
    token: str,
    email: str,
    full_name: str,
    role: str = "user"
) -> None:
    """
    Set authenticated user session state after successful login.
    
    Args:
        user_id: UUID of the authenticated user
        token: JWT access token
        email: User's email address
        full_name: User's full name
        role: User's access role ("user" or "admin")
    """
    st.session_state.user_id = user_id
    st.session_state.token = token
    st.session_state.user_email = email
    st.session_state.user_full_name = full_name
    st.session_state.user_role = role
    st.session_state.is_authenticated = True
    st.session_state.page = "chat"  # Redirect to chat on login


def logout_user() -> None:
    """Clear all authentication state and reset to login page."""
    st.session_state.user_id = None
    st.session_state.token = None
    st.session_state.user_email = None
    st.session_state.user_full_name = None
    st.session_state.user_role = "user"
    st.session_state.is_authenticated = False
    st.session_state.page = "login"
    st.session_state.messages = []
    st.session_state.current_conversation_id = None


def set_agent_processing(is_processing: bool, error_msg: Optional[str] = None) -> None:
    """
    Update agent processing state.
    
    Args:
        is_processing: True if agent is currently processing
        error_msg: Optional error message if processing failed
    """
    if error_msg:
        st.session_state.agent_status = "error"
        st.session_state.agent_error_message = error_msg
    else:
        st.session_state.agent_status = "processing" if is_processing else "idle"
        st.session_state.agent_error_message = None
    
    if not error_msg:
        st.session_state.last_agent_response_at = datetime.utcnow()


def update_usage_metrics(
    tokens_used: int = 0,
    requests_used: int = 0
) -> None:
    """
    Update token and request usage counters.
    
    Args:
        tokens_used: Number of tokens consumed in this request
        requests_used: Increment request count (usually 1)
    """
    st.session_state.usage_tokens_this_month += tokens_used
    st.session_state.usage_requests_today += requests_used


def get_auth_headers() -> dict:
    """
    Get HTTP headers for authenticated requests to the backend API.
    
    Returns:
        Dict with Authorization header if user is authenticated, empty dict otherwise.
    """
    if not is_authenticated():
        return {}
    
    return {
        "Authorization": f"Bearer {st.session_state.token}",
        "Content-Type": "application/json"
    }


def clear_messages() -> None:
    """Clear the current conversation messages."""
    st.session_state.messages = []


def add_message(role: str, content: str, metadata: Optional[dict] = None) -> None:
    """
    Add a message to the conversation.
    
    Args:
        role: "user" | "assistant" | "system" | "tool"
        content: Message text content
        metadata: Optional metadata (e.g., tool_calls, reasoning)
    """
    message = {
        "role": role,
        "content": content,
        "timestamp": datetime.utcnow().isoformat(),
    }
    if metadata:
        message.update(metadata)
    
    st.session_state.messages.append(message)


__all__ = [
    "init_session_state",
    "is_authenticated",
    "login_user",
    "logout_user",
    "set_agent_processing",
    "update_usage_metrics",
    "get_auth_headers",
    "clear_messages",
    "add_message",
]
