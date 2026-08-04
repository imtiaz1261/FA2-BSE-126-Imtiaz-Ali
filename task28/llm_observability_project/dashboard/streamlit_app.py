import streamlit as st
from chat_ui import render_chat
from analytics import render_dashboard

st.set_page_config(page_title="LLM Cost Optimization Assistant", layout="wide")

st.sidebar.title("LLM Cost Optimization Assistant")
page = st.sidebar.radio("Navigate", ["Chat", "Dashboard"])

if page == "Chat":
    render_chat()
else:
    render_dashboard()
