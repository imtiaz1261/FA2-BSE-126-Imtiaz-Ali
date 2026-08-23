"""
Streamlit application entrypoint.

Phase 6/7: the chat area now sends real messages to the LLM and
streams the reply back progressively. Phase 8 adds document upload,
management via the sidebar.
"""

import streamlit as st

from components.auth_forms import render_auth_gate
from components.chat import render_chat
from components.sidebar import render_sidebar
from config import settings
from state.session import init_session_state, is_authenticated

st.set_page_config(page_title=settings.APP_TITLE, page_icon="🧠", layout="wide")
init_session_state()

if not is_authenticated():
    render_auth_gate()
    st.stop()

render_sidebar()

st.title(settings.APP_TITLE)

conversation_id = st.session_state.get("current_conversation_id")
mode = st.session_state.get("mode", "Chat")

if conversation_id is None:
    st.info("Select a conversation from the sidebar, or start a new one.")
else:
    current = next(
        (c for c in st.session_state.get("conversations", []) if c["id"] == conversation_id),
        None,
    )
    title = current["title"] if current else "Conversation"
    st.subheader(f"{title} · {mode} mode")
    render_chat(conversation_id, mode)
