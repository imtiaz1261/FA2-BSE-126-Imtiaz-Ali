"""
Premium Auth UI — Login & Registration.
ChatGPT/Claude-inspired centered card with gradient hero background.
"""
import streamlit as st
from api_client.client import api_client
from state.session import log_in
from theme import inject_global_css, inject_page_bg, GLOBAL_CSS


_AUTH_CSS = """
<style>
.auth-hero {
    text-align: center;
    padding: 32px 0 24px;
    animation: fadeIn 0.5s ease;
}
.auth-logo {
    width: 56px; height: 56px;
    background: linear-gradient(135deg, #4f8ef7, #7c3aed);
    border-radius: 16px;
    display: inline-flex; align-items: center; justify-content: center;
    font-size: 1.8rem; margin-bottom: 16px;
    box-shadow: 0 8px 32px rgba(79,142,247,0.3);
}
.auth-title {
    color: #f0f4ff; font-size: 1.7rem; font-weight: 700;
    margin: 0 0 6px;
}
.auth-sub {
    color: #64748b; font-size: 0.9rem;
}
.auth-card {
    background: linear-gradient(145deg, #131d32, #0f1629);
    border: 1px solid #1e2d47;
    border-radius: 20px;
    padding: 32px;
    max-width: 440px;
    margin: 0 auto;
    box-shadow: 0 24px 64px rgba(0,0,0,0.4);
    animation: fadeInUp 0.4s ease;
}
.auth-divider {
    display: flex; align-items: center; gap: 12px;
    margin: 18px 0; color: #1e2d47;
}
.auth-divider::before, .auth-divider::after {
    content: ''; flex: 1; height: 1px; background: #1e2d47;
}
.auth-feature {
    display: flex; align-items: center; gap: 10px;
    padding: 10px 0; border-bottom: 1px solid #0f1629;
}
.auth-feature:last-child { border-bottom: none; }
</style>
"""


def render_auth_gate() -> None:
    inject_global_css()
    inject_page_bg()
    st.markdown(_AUTH_CSS, unsafe_allow_html=True)

    # Centre everything
    _, mid, _ = st.columns([1, 2, 1])

    with mid:
        # Hero
        st.markdown(
            '<div class="auth-hero">'
            '<div class="auth-logo">🧠</div>'
            '<div class="auth-title">AI Research Workspace</div>'
            '<div class="auth-sub">Your intelligent research & knowledge platform</div>'
            '</div>',
            unsafe_allow_html=True,
        )

        st.markdown('<div class="auth-card">', unsafe_allow_html=True)

        login_tab, register_tab = st.tabs(["Sign In", "Create Account"])

        # ── Login ────────────────────────────────────────────────────────────
        with login_tab:
            with st.form("login_form", clear_on_submit=False):
                st.markdown(
                    '<p style="color:#94a3b8;font-size:0.88rem;margin:0 0 16px;">Welcome back</p>',
                    unsafe_allow_html=True,
                )
                email    = st.text_input("Email address", placeholder="you@example.com",
                                         key="li_email")
                password = st.text_input("Password", type="password",
                                         placeholder="••••••••", key="li_pass")
                st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)
                submitted = st.form_submit_button(
                    "Sign In →", use_container_width=True, type="primary"
                )

            if submitted:
                if not email or not password:
                    st.error("Please enter your email and password.")
                else:
                    with st.spinner("Signing in…"):
                        result = api_client.login(email, password)
                    if result.ok:
                        log_in(result.data["access_token"], result.data["user"])
                        st.rerun()
                    else:
                        detail = result.error or "Login failed."
                        if isinstance(detail, dict):
                            detail = detail.get("message", str(detail))
                        st.error(f"✕ {detail}")

        # ── Register ─────────────────────────────────────────────────────────
        with register_tab:
            with st.form("register_form", clear_on_submit=False):
                st.markdown(
                    '<p style="color:#94a3b8;font-size:0.88rem;margin:0 0 16px;">'
                    'Get started — free forever</p>',
                    unsafe_allow_html=True,
                )
                full_name = st.text_input("Full name (optional)",
                                          placeholder="Alex Johnson", key="reg_name")
                email     = st.text_input("Email address",
                                          placeholder="you@example.com", key="reg_email")
                password  = st.text_input("Password", type="password",
                                          placeholder="Min. 8 characters", key="reg_pass",
                                          help="At least 8 characters.")
                st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)
                submitted = st.form_submit_button(
                    "Create Account →", use_container_width=True, type="primary"
                )

            if submitted:
                if not email or not password:
                    st.error("Email and password are required.")
                elif len(password) < 8:
                    st.error("Password must be at least 8 characters.")
                else:
                    with st.spinner("Creating account…"):
                        result = api_client.register(email, password, full_name)
                    if result.ok:
                        log_in(result.data["access_token"], result.data["user"])
                        st.rerun()
                    else:
                        detail = result.error or "Registration failed."
                        if isinstance(detail, dict):
                            detail = detail.get("message", str(detail))
                        st.error(f"✕ {detail}")

        st.markdown('</div>', unsafe_allow_html=True)

        # Feature list
        st.markdown('<div style="height:24px;"></div>', unsafe_allow_html=True)
        features = [
            ("💬", "ChatGPT-style AI conversations"),
            ("🔬", "Deep web research with citations"),
            ("📚", "RAG over your own documents"),
            ("🤖", "LangGraph agent with tools"),
        ]
        feature_html = ""
        for icon, text in features:
            feature_html += (
                f'<div class="auth-feature">'
                f'<span style="color:#4f8ef7;font-size:1.1rem;">{icon}</span>'
                f'<span style="color:#94a3b8;font-size:0.85rem;">{text}</span>'
                f'</div>'
            )
        st.markdown(
            f'<div style="max-width:440px;margin:0 auto;'
            f'background:#0a0f1e;border:1px solid #1e2d47;'
            f'border-radius:14px;padding:16px 20px;">'
            f'{feature_html}</div>',
            unsafe_allow_html=True,
        )
