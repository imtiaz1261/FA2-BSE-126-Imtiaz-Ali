"""Login and register forms, shown when the user isn't authenticated."""

import streamlit as st

from api_client.client import api_client
from state.session import log_in


def render_auth_gate() -> None:
    st.title("Welcome")
    st.caption("Sign in or create an account to continue.")

    login_tab, register_tab = st.tabs(["Log in", "Create account"])

    with login_tab:
        with st.form("login_form"):
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_password")
            submitted = st.form_submit_button("Log in", use_container_width=True)

        if submitted:
            if not email or not password:
                st.error("Please enter both email and password.")
            else:
                result = api_client.login(email, password)
                if result.ok:
                    log_in(result.data["access_token"], result.data["user"])
                    st.rerun()
                else:
                    st.error(result.error)

    with register_tab:
        with st.form("register_form"):
            full_name = st.text_input("Full name (optional)", key="register_name")
            email = st.text_input("Email", key="register_email")
            password = st.text_input(
                "Password", type="password", key="register_password", help="At least 8 characters."
            )
            submitted = st.form_submit_button("Create account", use_container_width=True)

        if submitted:
            if not email or not password:
                st.error("Please enter both email and password.")
            elif len(password) < 8:
                st.error("Password must be at least 8 characters.")
            else:
                result = api_client.register(email, password, full_name)
                if result.ok:
                    log_in(result.data["access_token"], result.data["user"])
                    st.rerun()
                else:
                    st.error(result.error)
