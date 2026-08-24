"""
frontend/pages/usage_page.py — Usage & Limits (3D glassmorphism)
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


def _progress_bar(value: int, limit: int, color: str) -> str:
    pct = min(value / limit * 100, 100) if limit else 0
    return f"""
    <div style="margin-top:12px">
        <div style="display:flex;justify-content:space-between;
                    font-size:0.78rem;color:var(--text-muted);margin-bottom:6px">
            <span>{value:,} used</span>
            <span>{limit - value:,} remaining</span>
        </div>
        <div style="background:rgba(255,255,255,0.06);
                    border-radius:99px;height:8px;overflow:hidden">
            <div style="width:{pct:.1f}%;background:{color};
                        border-radius:99px;height:8px;
                        transition:width 0.5s ease;
                        box-shadow:0 0 8px {color}66"></div>
        </div>
        <div style="text-align:right;font-size:0.72rem;
                    color:var(--text-muted);margin-top:4px">
            {pct:.1f}% of {limit:,}
        </div>
    </div>
    """


def render_usage_page() -> None:
    st.markdown("""
    <div class="page-header">
        <div class="page-title">📊 Usage &amp; Limits</div>
        <div class="page-subtitle">Track your token consumption and request quotas</div>
    </div>
    """, unsafe_allow_html=True)

    data = None
    try:
        r = requests.get(
            f"{settings.BACKEND_URL}/api/v1/subscriptions/usage",
            headers=get_auth_headers(),
            timeout=8,
        )
        if r.status_code == 200:
            data = r.json()
    except Exception:
        pass

    tokens_used   = (data or {}).get("tokens_used",       st.session_state.get("usage_tokens_this_month", 0))
    tokens_limit  = (data or {}).get("tokens_limit",      st.session_state.get("usage_tokens_limit", 50_000))
    req_today     = (data or {}).get("requests_today",    st.session_state.get("usage_requests_today", 0))
    req_limit     = (data or {}).get("requests_limit",    st.session_state.get("usage_requests_limit", 20))
    plan          = (data or {}).get("plan", "free")

    t_pct = tokens_used / max(tokens_limit, 1)
    r_pct = req_today  / max(req_limit,    1)

    t_color = "#10b981" if t_pct < 0.7 else "#f59e0b" if t_pct < 0.9 else "#ef4444"
    r_color = "#10b981" if r_pct < 0.7 else "#f59e0b" if r_pct < 0.9 else "#ef4444"

    plan_icon = {"free": "✦", "pro": "⚡", "enterprise": "🚀"}.get(plan, "✦")

    # plan badge row
    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:1.5rem">
        <span style="font-size:1.25rem">{plan_icon}</span>
        <span style="font-weight:700;color:var(--text-primary);
                     font-size:0.9375rem">{plan.title()} Plan</span>
        <span class="badge badge-{'purple' if plan=='enterprise' else 'blue' if plan=='pro' else 'blue'}">
            {plan.upper()}
        </span>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2, gap="medium")

    with col1:
        st.markdown(f"""
        <div class="glass-card">
            <div style="display:flex;align-items:center;gap:10px;margin-bottom:4px">
                <div style="font-size:1.25rem">⚡</div>
                <div style="font-size:0.8rem;font-weight:700;
                            color:var(--text-muted);text-transform:uppercase;
                            letter-spacing:0.08em">Monthly Tokens</div>
            </div>
            <div style="font-size:2.25rem;font-weight:800;
                        color:var(--text-primary);letter-spacing:-0.03em;
                        margin-top:6px">{tokens_used:,}</div>
            <div style="font-size:0.8rem;color:var(--text-muted)">
                of {tokens_limit:,} total
            </div>
            {_progress_bar(tokens_used, tokens_limit, t_color)}
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="glass-card">
            <div style="display:flex;align-items:center;gap:10px;margin-bottom:4px">
                <div style="font-size:1.25rem">🔄</div>
                <div style="font-size:0.8rem;font-weight:700;
                            color:var(--text-muted);text-transform:uppercase;
                            letter-spacing:0.08em">Daily Requests</div>
            </div>
            <div style="font-size:2.25rem;font-weight:800;
                        color:var(--text-primary);letter-spacing:-0.03em;
                        margin-top:6px">{req_today:,}</div>
            <div style="font-size:0.8rem;color:var(--text-muted)">
                of {req_limit:,} today
            </div>
            {_progress_bar(req_today, req_limit, r_color)}
        </div>
        """, unsafe_allow_html=True)

    # upgrade nudge
    if t_pct > 0.8 or r_pct > 0.8:
        st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
        st.markdown("""
        <div style="background:rgba(245,158,11,0.08);
                    border:1px solid rgba(245,158,11,0.25);
                    border-radius:12px;padding:14px 20px;
                    display:flex;align-items:center;gap:12px">
            <span style="font-size:1.25rem">⚠️</span>
            <div>
                <div style="font-weight:600;color:#fcd34d;font-size:0.9rem">
                    You're approaching your limit
                </div>
                <div style="font-size:0.8rem;color:var(--text-muted);margin-top:2px">
                    Upgrade your plan to avoid interruptions.
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        if st.button("Upgrade plan  →", type="primary", key="usage_upgrade"):
            st.session_state.page = "subscription"
            st.rerun()

    # usage history table (if available)
    if data and data.get("history"):
        st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)
        st.markdown('<div class="page-title" style="font-size:1.125rem;margin-bottom:8px">Usage History</div>',
                    unsafe_allow_html=True)
        import pandas as pd
        df = pd.DataFrame(data["history"])
        st.dataframe(df, use_container_width=True, hide_index=True)
