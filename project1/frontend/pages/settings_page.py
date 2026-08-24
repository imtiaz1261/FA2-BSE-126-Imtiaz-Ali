"""
frontend/pages/settings_page.py — User Settings (3D glassmorphism)
"""

import sys
from pathlib import Path
_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import streamlit as st
import requests
from backend.core.config import settings
from frontend.utils.session_state import get_auth_headers


def render_settings_page() -> None:
    st.markdown("""
    <div class="page-header">
        <div class="page-title">⚙️ Settings</div>
        <div class="page-subtitle">Manage your profile and security preferences</div>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["👤  Profile", "🔒  Security", "🎨  Appearance"])

    # ── Profile ──────────────────────────────────────────────
    with tab1:
        email     = st.session_state.get("user_email", "")
        full_name = st.session_state.get("user_full_name", "")
        role      = st.session_state.get("user_role", "user")
        initials  = (full_name[:2] if full_name else "U").upper()

        st.markdown(f"""
        <div class="glass-card" style="display:flex;align-items:center;
                    gap:20px;margin-bottom:1.5rem">
            <div class="avatar" style="width:60px;height:60px;
                 font-size:1.375rem">{initials}</div>
            <div>
                <div style="font-size:1.125rem;font-weight:700;
                            color:var(--text-primary)">{full_name or 'User'}</div>
                <div style="font-size:0.875rem;color:var(--text-muted);
                            margin-top:2px">{email}</div>
                <div style="margin-top:6px">
                    <span class="badge {'badge-purple' if role=='admin' else 'badge-blue'}">
                        {role.title()}
                    </span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        with st.form("profile_form"):
            new_name = st.text_input(
                "Full name",
                value=full_name,
                placeholder="Your display name",
            )
            st.text_input(
                "Email address",
                value=email,
                disabled=True,
                help="Email cannot be changed after registration",
            )
            st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
            if st.form_submit_button("Save changes", type="primary",
                                     use_container_width=True):
                if not new_name or len(new_name.strip()) < 2:
                    st.error("Full name must be at least 2 characters.")
                else:
                    try:
                        r = requests.patch(
                            f"{settings.BACKEND_URL}/api/v1/auth/me",
                            headers=get_auth_headers(),
                            json={"full_name": new_name.strip()},
                            timeout=10,
                        )
                        if r.status_code == 200:
                            st.session_state.user_full_name = new_name.strip()
                            st.success("Profile updated!")
                        else:
                            st.error(r.json().get("detail", "Update failed"))
                    except Exception as exc:
                        st.error(f"Connection error: {exc}")

    # ── Security ─────────────────────────────────────────────
    with tab2:
        st.markdown("""
        <div style="margin-bottom:1.25rem">
            <div style="font-size:0.9375rem;font-weight:600;
                        color:var(--text-primary)">Change password</div>
            <div style="font-size:0.8rem;color:var(--text-muted);margin-top:3px">
                Use a strong password with uppercase, lowercase, digit, and special character.
            </div>
        </div>
        """, unsafe_allow_html=True)

        with st.form("password_form"):
            current_pwd = st.text_input(
                "Current password",
                type="password",
                placeholder="••••••••",
            )
            new_pwd = st.text_input(
                "New password",
                type="password",
                placeholder="Min 8 characters",
            )
            confirm_pwd = st.text_input(
                "Confirm new password",
                type="password",
                placeholder="Repeat new password",
            )
            st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
            if st.form_submit_button("Update password", type="primary",
                                     use_container_width=True):
                if not all([current_pwd, new_pwd, confirm_pwd]):
                    st.error("All fields are required.")
                elif new_pwd != confirm_pwd:
                    st.error("New passwords do not match.")
                elif len(new_pwd) < 8:
                    st.error("Password must be at least 8 characters.")
                else:
                    try:
                        r = requests.post(
                            f"{settings.BACKEND_URL}/api/v1/auth/me/password",
                            headers=get_auth_headers(),
                            json={
                                "current_password": current_pwd,
                                "new_password": new_pwd,
                            },
                            timeout=10,
                        )
                        if r.status_code == 200:
                            st.success("Password changed successfully!")
                        else:
                            st.error(r.json().get("detail", "Password change failed"))
                    except Exception as exc:
                        st.error(f"Connection error: {exc}")

        st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)
        st.markdown("""
        <div class="glass-card" style="border-color:rgba(239,68,68,0.25)">
            <div style="font-size:0.9375rem;font-weight:700;color:#fca5a5;
                        margin-bottom:6px">Danger zone</div>
            <div style="font-size:0.8rem;color:var(--text-muted)">
                Deleting your account is permanent and cannot be undone.
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        if st.button("Delete my account", key="delete_account"):
            st.error("Account deletion is not yet implemented in this build.")

    # ── Appearance ───────────────────────────────────────────
    with tab3:
        st.markdown('<div style="margin-bottom:1rem;font-size:0.875rem;'
                    'color:var(--text-muted)">UI Preferences</div>',
                    unsafe_allow_html=True)

        current_theme = st.session_state.get("theme", "dark")
        theme_choice  = st.radio(
            "Color theme",
            ["dark", "light"],
            index=0 if current_theme == "dark" else 1,
            horizontal=True,
            format_func=lambda x: "🌙 Dark" if x == "dark" else "☀️ Light",
        )
        if theme_choice != current_theme:
            st.session_state.theme = theme_choice
            st.rerun()

        st.markdown("<hr>", unsafe_allow_html=True)
        show_logs = st.toggle(
            "Show agent reasoning logs",
            value=st.session_state.get("show_agent_logs", False),
        )
        if show_logs != st.session_state.get("show_agent_logs", False):
            st.session_state.show_agent_logs = show_logs
