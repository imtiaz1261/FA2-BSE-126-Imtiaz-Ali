"""
Streamlit application entrypoint.

Phase 2: proves the full round trip — Streamlit calls the FastAPI
/api/health endpoint through the ApiClient and renders the result,
with graceful error handling if the backend isn't reachable.
"""

import streamlit as st

from api_client.client import api_client
from config import settings

st.set_page_config(page_title=settings.APP_TITLE, page_icon="🧠", layout="wide")

st.title(settings.APP_TITLE)
st.caption("Phase 2 — Streamlit ↔ FastAPI end-to-end connection")

result = api_client.health_check()

if result.ok:
    st.success(f"Backend is reachable — status: **{result.data['status']}**")
    st.json(result.data)
else:
    st.error(result.error)
    st.info(
        f"Make sure the backend is running at `{settings.API_BASE_URL}` "
        "(see README for the run command)."
    )
