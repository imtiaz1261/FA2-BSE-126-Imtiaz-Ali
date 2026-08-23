"""Chat UI: message history, chat input, streaming assistant replies (Phase 6/7)."""

from typing import Generator

import streamlit as st

from api_client.client import api_client


def _load_history(token: str, conversation_id: str) -> None:
    result = api_client.list_messages(token, conversation_id)
    st.session_state.setdefault("messages", {})
    if result.ok:
        st.session_state["messages"][conversation_id] = [
            {"role": m["role"], "content": m["content"]} for m in result.data
        ]
    else:
        st.session_state["messages"][conversation_id] = []
        st.error(result.error)


def _consume_stream(
    token: str, conversation_id: str, prompt: str, mode: str, sink: dict
) -> Generator[str, None, None]:
    """Adapts the client's (kind, payload) tuples into plain text chunks
    for st.write_stream, while recording the full text / any error in `sink`
    so the caller can persist it locally and show errors after streaming ends."""
    for kind, payload in api_client.stream_message(token, conversation_id, prompt, mode):
        if kind == "__error__":
            sink["error"] = payload
            return
        sink["full_text"] += payload
        yield payload


def render_chat(conversation_id: str, mode: str) -> None:
    token = st.session_state["access_token"]

    if conversation_id not in st.session_state.get("messages", {}):
        _load_history(token, conversation_id)

    for msg in st.session_state["messages"].get(conversation_id, []):
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    prompt = st.chat_input("Message the assistant...")
    if not prompt:
        return

    st.session_state["messages"][conversation_id].append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    sink = {"full_text": "", "error": None}
    with st.chat_message("assistant"):
        st.write_stream(_consume_stream(token, conversation_id, prompt, mode, sink))

    if sink["error"]:
        st.error(f"Couldn't get a reply: {sink['error']}")
    elif sink["full_text"]:
        st.session_state["messages"][conversation_id].append(
            {"role": "assistant", "content": sink["full_text"]}
        )
