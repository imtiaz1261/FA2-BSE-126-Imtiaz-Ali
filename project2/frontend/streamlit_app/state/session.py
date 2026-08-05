"""Central place for Streamlit session_state defaults and small helpers."""

import streamlit as st

DEFAULTS = {
    "access_token": None,
    "user": None,
    "conversations": [],
    "current_conversation_id": None,
    "mode": "Chat",
}


def init_session_state() -> None:
    for key, default in DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = default


def is_authenticated() -> bool:
    return st.session_state.get("access_token") is not None


def log_in(access_token: str, user: dict) -> None:
    st.session_state["access_token"] = access_token
    # Ensure is_admin is always present (Phase 18)
    if "is_admin" not in user:
        user["is_admin"] = False
    st.session_state["user"] = user


def log_out() -> None:
    for key, default in DEFAULTS.items():
        st.session_state[key] = default
