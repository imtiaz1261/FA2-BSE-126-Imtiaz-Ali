"""
streamlit_app.py
-----------------
Streamlit interface for the Multi-Step Research Assistant. Calls the
FastAPI backend (api.py) over HTTP -- so run both:

    uvicorn api:app --host 127.0.0.1 --port 8000
    streamlit run streamlit_app.py

in separate terminals.
"""

import requests
import streamlit as st

from config import API_HOST, API_PORT

API_BASE_URL = f"http://{API_HOST}:{API_PORT}"

st.set_page_config(page_title="Multi-Step Research Assistant", page_icon="\U0001F50D", layout="wide")

st.title("\U0001F50D Multi-Step Research Assistant")
st.caption("LangGraph-powered: plan \u2192 search \u2192 validate/retry \u2192 summarize \u2192 report")

if "last_result" not in st.session_state:
    st.session_state.last_result = None

with st.sidebar:
    st.header("About")
    st.write(
        "This assistant decomposes your question into sub-tasks, searches "
        "the web for each, validates result quality (retrying insufficient "
        "searches), summarizes findings, and writes a structured report."
    )
    try:
        health = requests.get(f"{API_BASE_URL}/health", timeout=3)
        if health.ok:
            st.success("Backend connected")
        else:
            st.error("Backend reachable but unhealthy")
    except requests.RequestException:
        st.error(f"Cannot reach API at {API_BASE_URL}.\nStart it with:\nuvicorn api:app --port {API_PORT}")

    if st.button("Show LangGraph workflow diagram"):
        try:
            resp = requests.get(f"{API_BASE_URL}/graph/mermaid", timeout=10)
            resp.raise_for_status()
            st.code(resp.json()["mermaid"], language="mermaid")
            st.caption("Paste this into https://mermaid.live to render it visually.")
        except requests.RequestException as exc:
            st.error(f"Could not fetch diagram: {exc}")

query = st.text_input("Research question", placeholder="e.g. What are the latest advances in solid-state batteries?")
run_clicked = st.button("Run Research", type="primary")

if run_clicked:
    if not query.strip():
        st.warning("Please enter a research question.")
    else:
        with st.spinner("Researching... this can take a minute for multi-task queries."):
            try:
                resp = requests.post(f"{API_BASE_URL}/research", json={"query": query}, timeout=300)
                resp.raise_for_status()
                st.session_state.last_result = resp.json()
            except requests.RequestException as exc:
                detail = ""
                if exc.response is not None:
                    try:
                        detail = exc.response.json().get("detail", "")
                    except ValueError:
                        detail = exc.response.text
                st.error(f"Research request failed: {detail or exc}")
                st.session_state.last_result = None

result = st.session_state.last_result
if result:
    st.subheader(result["report_title"] or "Research Report")

    tab_report, tab_log, tab_tasks = st.tabs(["Report", "Execution Log", "Research Tasks"])

    with tab_report:
        st.markdown(result["report_markdown"])
        if result["errors"]:
            st.warning("Non-fatal issues encountered during this run:")
            for err in result["errors"]:
                st.write(f"- {err}")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Prepare PDF download"):
                try:
                    pdf_resp = requests.get(
                        f"{API_BASE_URL}/report/{result['run_id']}/export",
                        params={"fmt": "pdf"}, timeout=60,
                    )
                    pdf_resp.raise_for_status()
                    st.download_button(
                        "Download PDF", data=pdf_resp.content,
                        file_name=f"{result['run_id']}.pdf", mime="application/pdf",
                    )
                except requests.RequestException as exc:
                    st.error(f"PDF export failed: {exc}")
        with col2:
            if st.button("Prepare DOCX download"):
                try:
                    docx_resp = requests.get(
                        f"{API_BASE_URL}/report/{result['run_id']}/export",
                        params={"fmt": "docx"}, timeout=60,
                    )
                    docx_resp.raise_for_status()
                    st.download_button(
                        "Download DOCX", data=docx_resp.content,
                        file_name=f"{result['run_id']}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    )
                except requests.RequestException as exc:
                    st.error(f"DOCX export failed: {exc}")

    with tab_log:
        st.write("Node-by-node execution history for this run:")
        for entry in result["node_log"]:
            st.text(entry)

    with tab_tasks:
        st.write(f"**Objective:** {result['objective']}")
        for i, task in enumerate(result["tasks"], start=1):
            st.write(f"{i}. {task}")
