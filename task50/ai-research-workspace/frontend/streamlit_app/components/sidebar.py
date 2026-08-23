"""Sidebar: user info, mode switcher, conversation history, documents, logout."""

import streamlit as st

from api_client.client import api_client
from components.documents import render_document_manager
from state.session import log_out

MODES = ["Chat", "Knowledge (RAG)", "Research", "Agent"]


def _load_conversations() -> None:
    token = st.session_state["access_token"]
    result = api_client.list_conversations(token)
    if result.ok:
        st.session_state["conversations"] = result.data
    else:
        st.session_state["conversations"] = []
        st.sidebar.error(result.error)


def render_sidebar() -> None:
    user = st.session_state["user"]

    with st.sidebar:
        st.markdown(f"**{user.get('full_name') or user['email']}**")
        st.caption(f"{user['email']} · {user['plan']} plan")

        if st.button("Log out", use_container_width=True):
            log_out()
            st.rerun()

        st.divider()

        st.selectbox("Mode", MODES, key="mode")

        st.divider()

        if "conversations" not in st.session_state or not st.session_state["conversations"]:
            _load_conversations()

        if st.button("+ New conversation", use_container_width=True):
            token = st.session_state["access_token"]
            result = api_client.create_conversation(token)
            if result.ok:
                _load_conversations()
                st.session_state["current_conversation_id"] = result.data["id"]
                st.rerun()
            else:
                st.error(result.error)

        st.caption("Conversations")
        for convo in st.session_state.get("conversations", []):
            is_current = convo["id"] == st.session_state.get("current_conversation_id")
            cols = st.columns([6, 1, 1])
            with cols[0]:
                label = f"➤ {convo['title']}" if is_current else convo["title"]
                if st.button(label, key=f"select_{convo['id']}", use_container_width=True):
                    st.session_state["current_conversation_id"] = convo["id"]
                    st.rerun()
            with cols[1]:
                if st.button("✎", key=f"rename_{convo['id']}", help="Rename"):
                    st.session_state[f"renaming_{convo['id']}"] = True
            with cols[2]:
                if st.button("🗑", key=f"delete_{convo['id']}", help="Delete"):
                    token = st.session_state["access_token"]
                    result = api_client.delete_conversation(token, convo["id"])
                    if result.ok:
                        if st.session_state.get("current_conversation_id") == convo["id"]:
                            st.session_state["current_conversation_id"] = None
                        _load_conversations()
                        st.rerun()
                    else:
                        st.error(result.error)

            if st.session_state.get(f"renaming_{convo['id']}"):
                new_title = st.text_input(
                    "New title", value=convo["title"], key=f"new_title_{convo['id']}"
                )
                if st.button("Save", key=f"save_{convo['id']}"):
                    token = st.session_state["access_token"]
                    result = api_client.rename_conversation(token, convo["id"], new_title)
                    if result.ok:
                        st.session_state[f"renaming_{convo['id']}"] = False
                        _load_conversations()
                        st.rerun()
                    else:
                        st.error(result.error)

        st.divider()
        with st.expander("📄 Documents"):
            render_document_manager()
