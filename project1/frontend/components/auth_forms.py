"""
frontend/components/auth_forms.py — 3D Glassmorphism Auth Pages
================================================================
Login and registration with glassmorphism cards, gradient accents,
inline validation, and auto-login after registration.
"""

import sys
from pathlib import Path
_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import streamlit as st
import requests
from backend.core.config import settings


# ── shared auth page CSS ──────────────────────────────────────────────────
_AUTH_CSS = """
<style>
.auth-wrap {
    display: flex; align-items: center; justify-content: center;
    min-height: 80vh; padding: 2rem;
}
.auth-card {
    background: rgba(15, 22, 41, 0.92);
    border: 1px solid rgba(255,255,255,0.10);
    border-radius: 24px;
    padding: 2.5rem 2.75rem;
    width: 100%; max-width: 440px;
    backdrop-filter: blur(24px);
    box-shadow: 0 24px 64px rgba(0,0,0,0.5),
                0 1px 0 rgba(255,255,255,0.08) inset;
    position: relative; overflow: hidden;
}
.auth-card::before {
    content: '';
    position: absolute; top: 0; left: 0; right: 0; height: 1px;
    background: linear-gradient(90deg,
        transparent 0%, rgba(99,102,241,0.6) 50%, transparent 100%);
}
.auth-logo {
    font-size: 1.625rem; font-weight: 800;
    background: linear-gradient(135deg, #a5b4fc 0%, #67e8f9 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    background-clip: text; letter-spacing: -0.03em;
    text-align: center; margin-bottom: 4px;
}
.auth-title {
    font-size: 1.375rem; font-weight: 700;
    color: #f1f5f9; text-align: center;
    margin: 0 0 4px; letter-spacing: -0.02em;
}
.auth-sub {
    font-size: 0.875rem; color: #64748b;
    text-align: center; margin: 0 0 1.75rem;
}
.auth-divider {
    border: none; border-top: 1px solid rgba(255,255,255,0.08);
    margin: 1.5rem 0;
}
.auth-footer {
    text-align: center; font-size: 0.8125rem; color: #64748b; margin-top: 1rem;
}
.auth-footer a { color: #a5b4fc; text-decoration: none; font-weight: 600; }

/* glow orbs */
.orb {
    position: fixed; border-radius: 50%;
    filter: blur(80px); pointer-events: none; z-index: 0;
}
.orb-1 {
    width: 400px; height: 400px;
    background: rgba(99,102,241,0.12);
    top: -100px; left: -100px;
}
.orb-2 {
    width: 300px; height: 300px;
    background: rgba(6,182,212,0.08);
    bottom: -80px; right: -80px;
}

/* password strength bar */
.pwd-bar { height: 3px; border-radius: 99px; transition: all 0.3s ease; }
</style>
<div class="orb orb-1"></div>
<div class="orb orb-2"></div>
"""


def _error(msg):
    """Uniform error display."""
    if isinstance(msg, list):
        lines = " · ".join(e.get("msg", str(e)) for e in msg)
        st.error(lines)
    else:
        st.error(str(msg))


# ── Login ─────────────────────────────────────────────────────────────────
def render_login_page() -> None:
    st.markdown(_AUTH_CSS, unsafe_allow_html=True)

    _, mid, _ = st.columns([1, 1.8, 1])
    with mid:
        st.markdown("""
        <div class="auth-card">
            <div class="auth-logo">✦ AIHub</div>
            <h2 class="auth-title">Welcome back</h2>
            <p class="auth-sub">Sign in to your account to continue</p>
        </div>
        """, unsafe_allow_html=True)

        # form inside the same visual column
        with st.form("login_form", clear_on_submit=False):
            email = st.text_input(
                "Email address",
                placeholder="you@example.com",
                key="login_email_field",
            )
            password = st.text_input(
                "Password",
                type="password",
                placeholder="••••••••",
                key="login_password_field",
            )

            st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
            submitted = st.form_submit_button(
                "Sign in  →",
                use_container_width=True,
                type="primary",
            )

        if submitted:
            if not email or not password:
                st.error("Email and password are required.")
            else:
                with st.spinner("Authenticating…"):
                    try:
                        resp = requests.post(
                            f"{settings.BACKEND_URL}/api/v1/auth/login",
                            json={"email": email, "password": password},
                            timeout=10,
                        )
                    except requests.RequestException:
                        st.error("Cannot reach the server. Is the backend running?")
                        return

                if resp.status_code == 200:
                    data = resp.json()
                    from frontend.utils.session_state import login_user
                    login_user(
                        user_id=data["user"]["id"],
                        token=data["access_token"],
                        email=data["user"]["email"],
                        full_name=data["user"]["full_name"],
                        role=data["user"]["role"],
                    )
                    st.success("Signed in!")
                    st.rerun()
                else:
                    detail = resp.json().get("detail", "Login failed")
                    _error(detail)

        st.markdown("""
        <div class="auth-footer">
            Don't have an account?
            &nbsp;<a href="#" id="go_register">Create one</a>
        </div>
        """, unsafe_allow_html=True)

        if st.button("Create new account", use_container_width=True, key="go_reg"):
            st.session_state.page = "register"
            st.rerun()


# ── Register ──────────────────────────────────────────────────────────────
def render_register_page() -> None:
    st.markdown(_AUTH_CSS, unsafe_allow_html=True)

    _, mid, _ = st.columns([1, 1.8, 1])
    with mid:
        st.markdown("""
        <div class="auth-card">
            <div class="auth-logo">✦ AIHub</div>
            <h2 class="auth-title">Create your account</h2>
            <p class="auth-sub">Join thousands of users building with AI</p>
        </div>
        """, unsafe_allow_html=True)

        with st.form("register_form", clear_on_submit=False):
            full_name = st.text_input(
                "Full name",
                placeholder="Ada Lovelace",
                key="reg_name",
            )
            email = st.text_input(
                "Email address",
                placeholder="you@example.com",
                key="reg_email",
            )
            c1, c2 = st.columns(2)
            with c1:
                password = st.text_input(
                    "Password",
                    type="password",
                    placeholder="Min 8 chars",
                    key="reg_pwd",
                )
            with c2:
                confirm = st.text_input(
                    "Confirm password",
                    type="password",
                    placeholder="Repeat password",
                    key="reg_pwd2",
                )

            # password rules hint
            st.markdown("""
            <div style="font-size:0.72rem;color:var(--text-muted);
                        margin:2px 0 8px;line-height:1.6">
                Must contain uppercase, lowercase, digit &amp; special character.
            </div>
            """, unsafe_allow_html=True)

            st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
            submitted = st.form_submit_button(
                "Create account  →",
                use_container_width=True,
                type="primary",
            )

        if submitted:
            errors = []
            if not full_name or len(full_name.strip()) < 2:
                errors.append("Full name must be at least 2 characters.")
            if not email:
                errors.append("Email is required.")
            if not password or len(password) < 8:
                errors.append("Password must be at least 8 characters.")
            if password != confirm:
                errors.append("Passwords do not match.")

            if errors:
                for e in errors:
                    st.error(e)
            else:
                with st.spinner("Creating account…"):
                    try:
                        resp = requests.post(
                            f"{settings.BACKEND_URL}/api/v1/auth/register",
                            json={
                                "email": email,
                                "full_name": full_name.strip(),
                                "password": password,
                                "confirm_password": confirm,
                            },
                            timeout=10,
                        )
                    except requests.RequestException:
                        st.error("Cannot reach the server. Is the backend running?")
                        return

                if resp.status_code == 201:
                    # auto-login
                    with st.spinner("Signing you in…"):
                        try:
                            login_resp = requests.post(
                                f"{settings.BACKEND_URL}/api/v1/auth/login",
                                json={"email": email, "password": password},
                                timeout=10,
                            )
                        except requests.RequestException:
                            st.success("Account created! Please sign in.")
                            st.session_state.page = "login"
                            st.rerun()
                            return

                    if login_resp.status_code == 200:
                        token_data = login_resp.json()
                        from frontend.utils.session_state import login_user
                        login_user(
                            user_id=token_data["user"]["id"],
                            token=token_data["access_token"],
                            email=token_data["user"]["email"],
                            full_name=token_data["user"]["full_name"],
                            role=token_data["user"]["role"],
                        )
                        st.success("Account created! Welcome to AIHub.")
                        st.rerun()
                    else:
                        st.success("Account created! Please sign in.")
                        st.session_state.page = "login"
                        st.rerun()
                else:
                    detail = resp.json().get("detail", "Registration failed")
                    _error(detail)

        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
        if st.button("Already have an account? Sign in", use_container_width=True, key="go_login"):
            st.session_state.page = "login"
            st.rerun()
