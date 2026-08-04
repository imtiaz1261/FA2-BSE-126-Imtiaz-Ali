import os
import streamlit as st
import httpx

# Allow overriding the API base URL via environment for flexibility when
# the API server runs on a non-default port or host.
API_URL = os.getenv("API_URL", "http://localhost:8000")


def render_chat():
    st.title("💬 Chat")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    col1, col2 = st.columns([1, 3])
    with col1:
        st.subheader("Settings")
        use_cache = st.checkbox("Use cache", value=True)
        optimize_prompt = st.checkbox("Optimize prompt", value=True)
        if st.button("New chat"):
            st.session_state.messages = []
            st.rerun()

    with col2:
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                if msg["role"] == "assistant" and "meta" in msg:
                    m = msg["meta"]
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Tokens", m["total_tokens"])
                    c2.metric("Latency", f"{m['latency_ms']} ms")
                    c3.metric("Cost", f"£{m['estimated_cost_gbp']:.6f}")
                    c4.metric("Cache", "HIT" if m["cache_hit"] else "MISS")

        prompt = st.chat_input("Ask anything...")
        if prompt:
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    try:
                        r = httpx.post(f"{API_URL}/chat", json={
                            "message": prompt,
                            "use_cache": use_cache,
                            "optimize_prompt": optimize_prompt,
                        }, timeout=30)
                        # If backend returned an error (e.g. 500), avoid KeyError
                        if r.status_code != 200:
                            # Try to show helpful error detail when available
                            try:
                                err = r.json().get("detail")
                            except Exception:
                                err = r.text
                            # If it's a 404, hint that the API may be running on a
                            # different port or a different service is bound to
                            # the expected port (common on developer machines).
                            if r.status_code == 404:
                                st.error(
                                    f"Request failed: 404 Not Found — check that the API server is running at {API_URL} and that the /chat route is available."
                                )
                            else:
                                st.error(f"Request failed: {r.status_code} {err}")
                        else:
                            data = r.json()
                            st.markdown(data.get("response", "(no response)"))
                            st.session_state.messages.append({
                                "role": "assistant",
                                "content": data.get("response", ""),
                                "meta": data,
                            })
                    except Exception as e:
                        st.error(f"Request failed: {e}")
