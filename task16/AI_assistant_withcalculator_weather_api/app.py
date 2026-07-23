"""
Streamlit web interface.

Run with:  streamlit run app.py
"""

import streamlit as st

from assistant.agent import Assistant, AssistantError

st.set_page_config(page_title="AI Assistant", page_icon="🤖", layout="centered")

st.title("🤖 AI Assistant")
st.caption("Ask general questions, do math, or check the weather.")

# --- Init assistant (once per session) ---
if "assistant" not in st.session_state:
    try:
        st.session_state.assistant = Assistant()
        st.session_state.init_error = None
    except AssistantError as exc:
        st.session_state.assistant = None
        st.session_state.init_error = str(exc)

if "messages" not in st.session_state:
    st.session_state.messages = []  # for display only: [{"role": ..., "content": ...}]

if st.session_state.init_error:
    st.error(f"Startup error: {st.session_state.init_error}")
    st.info("Add your GROQ_API_KEY (and OPENWEATHER_API_KEY) to a .env file next to this app, then rerun.")
    st.stop()

# --- Sidebar ---
with st.sidebar:
    st.subheader("Session")
    if st.button("🗑️ Clear conversation"):
        st.session_state.assistant.reset()
        st.session_state.messages = []
        st.rerun()

    st.markdown("---")
    st.markdown("**Try asking:**")
    examples = [
        "What is 245 × 78?",
        "Calculate the square root of 625.",
        "What's the weather in Lahore today?",
        "Will it rain tomorrow in Karachi?",
        "Who invented Python?",
        "Summarize the benefits of machine learning.",
    ]
    for ex in examples:
        st.markdown(f"- {ex}")

# --- Chat history display ---
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# --- Chat input ---
user_input = st.chat_input("Ask me anything...")
if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            reply = st.session_state.assistant.ask(user_input)
        st.markdown(reply)

    st.session_state.messages.append({"role": "assistant", "content": reply})
