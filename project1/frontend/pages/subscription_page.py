"""
frontend/pages/subscription_page.py — 3D Subscription / Pricing Page
======================================================================
Glassmorphism pricing cards with hover 3D effects, plan comparison
table, and current plan indicator.
"""

import sys
from pathlib import Path
_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import streamlit as st
import requests
from datetime import datetime
from backend.core.config import settings
from frontend.utils.session_state import get_auth_headers

# ── plan data ─────────────────────────────────────────────────────────────
PLANS = [
    {
        "key":    "free",
        "name":   "Free",
        "price":  "0",
        "period": "forever",
        "color":  "#94a3b8",
        "icon":   "✦",
        "desc":   "Great for personal projects and exploration.",
        "popular": False,
        "features": [
            ("50,000 tokens / month",       True),
            ("20 requests / day",            True),
            ("Basic AI chat",                True),
            ("Document upload (5 files)",    True),
            ("Community support",            True),
            ("Priority processing",          False),
            ("Advanced agent tools",         False),
            ("API access",                   False),
        ],
    },
    {
        "key":    "pro",
        "name":   "Pro",
        "price":  "19",
        "period": "per month",
        "color":  "#6366f1",
        "icon":   "⚡",
        "desc":   "For professionals who need more power.",
        "popular": True,
        "features": [
            ("500,000 tokens / month",       True),
            ("500 requests / day",           True),
            ("Advanced AI chat + RAG",       True),
            ("Document upload (50 files)",   True),
            ("Priority support",             True),
            ("Priority processing",          True),
            ("Advanced agent tools",         True),
            ("API access",                   False),
        ],
    },
    {
        "key":    "enterprise",
        "name":   "Enterprise",
        "price":  "99",
        "period": "per month",
        "color":  "#06b6d4",
        "icon":   "🚀",
        "desc":   "For teams and high-volume workloads.",
        "popular": False,
        "features": [
            ("5,000,000 tokens / month",     True),
            ("10,000 requests / day",        True),
            ("Full AI suite",                True),
            ("Unlimited document upload",    True),
            ("Dedicated support",            True),
            ("Priority processing",          True),
            ("Advanced agent tools",         True),
            ("API access",                   True),
        ],
    },
]


def _fetch_current_sub() -> dict:
    try:
        r = requests.get(
            f"{settings.BACKEND_URL}/api/v1/subscriptions/current",
            headers=get_auth_headers(),
            timeout=8,
        )
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return {}


def _upgrade(plan_key: str) -> None:
    try:
        r = requests.post(
            f"{settings.BACKEND_URL}/api/v1/subscriptions/upgrade",
            headers=get_auth_headers(),
            json={"plan": plan_key},
            timeout=10,
        )
        if r.status_code == 200:
            st.success(f"Upgraded to {plan_key.title()} plan!")
            st.rerun()
        else:
            detail = r.json().get("detail", "Upgrade failed")
            st.error(detail)
    except Exception as exc:
        st.error(f"Connection error: {exc}")


def render_subscription_page() -> None:
    # ── page header ──────────────────────────────────────────
    st.markdown("""
    <div class="page-header">
        <div style="text-align:center;padding-bottom:0.5rem">
            <div class="page-title" style="font-size:2.25rem">
                Choose your plan
            </div>
            <div class="page-subtitle" style="font-size:1rem;margin-top:6px">
                Start free, scale as you grow.
                No hidden fees, cancel anytime.
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── current subscription banner ───────────────────────────
    current = _fetch_current_sub()
    current_plan = current.get("plan", "free")
    period_end   = current.get("current_period_end", "")
    status_val   = current.get("status", "active")

    if period_end:
        try:
            end_dt  = datetime.fromisoformat(period_end.replace("Z", "+00:00"))
            end_str = end_dt.strftime("%b %d, %Y")
        except Exception:
            end_str = period_end[:10]
    else:
        end_str = "—"

    badge_color = {"active": "#10b981", "trialing": "#f59e0b", "canceled": "#ef4444"}.get(
        status_val, "#94a3b8"
    )
    plan_icon = {"free": "✦", "pro": "⚡", "enterprise": "🚀"}.get(current_plan, "✦")

    st.markdown(f"""
    <div style="background:rgba(99,102,241,0.07);
                border:1px solid rgba(99,102,241,0.2);
                border-radius:16px;padding:16px 24px;
                display:flex;align-items:center;justify-content:space-between;
                margin-bottom:2rem;flex-wrap:wrap;gap:12px">
        <div style="display:flex;align-items:center;gap:14px">
            <div style="font-size:1.5rem">{plan_icon}</div>
            <div>
                <div style="font-weight:700;color:#f1f5f9;font-size:0.9375rem">
                    Current plan: {current_plan.title()}
                </div>
                <div style="font-size:0.8rem;color:#94a3b8;margin-top:2px">
                    Renews on {end_str}
                </div>
            </div>
        </div>
        <div style="display:flex;align-items:center;gap:8px">
            <div style="width:8px;height:8px;border-radius:50%;
                        background:{badge_color};
                        box-shadow:0 0 8px {badge_color}66"></div>
            <span style="font-size:0.8125rem;font-weight:600;
                         color:{badge_color};text-transform:capitalize">
                {status_val}
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── pricing cards ─────────────────────────────────────────
    cols = st.columns(3, gap="medium")

    for col, plan in zip(cols, PLANS):
        is_current = plan["key"] == current_plan
        is_popular = plan["popular"]

        features_html = "".join(
            f"""<div class="price-feature">
                  <span class="check" style="color:{'var(--accent-green)' if ok else 'var(--text-muted)'}">
                    {'✓' if ok else '✗'}
                  </span>
                  <span style="{'color:var(--text-secondary)' if ok else 'color:var(--text-muted);text-decoration:line-through'}">
                    {feat}
                  </span>
                </div>"""
            for feat, ok in plan["features"]
        )

        popular_tag = (
            '<span class="popular-tag">Most Popular</span>'
            if is_popular else ""
        )
        current_tag = (
            '<span style="position:absolute;top:16px;right:16px;'
            'background:rgba(16,185,129,0.18);color:#6ee7b7;'
            'font-size:0.7rem;font-weight:700;padding:3px 10px;'
            'border-radius:99px;border:1px solid rgba(16,185,129,0.3)">'
            'Current</span>'
            if is_current else ""
        )

        popular_class = "popular" if is_popular else ""
        glow = f"box-shadow:0 0 0 2px {plan['color']}33, 0 24px 60px rgba(0,0,0,0.5);" if is_popular else ""

        with col:
            st.markdown(f"""
            <div class="price-card {popular_class}" style="{glow}">
                {popular_tag}{current_tag}
                <div style="color:{plan['color']};font-size:1.75rem;margin-bottom:8px">
                    {plan['icon']}
                </div>
                <div class="price-name" style="color:{plan['color']}">{plan['name']}</div>
                <div style="display:flex;align-items:baseline;gap:4px;margin:8px 0">
                    <span class="price-amount">${plan['price']}</span>
                    <span class="price-period">/{plan['period']}</span>
                </div>
                <div class="price-desc">{plan['desc']}</div>
                <hr style="border-color:rgba(255,255,255,0.06);margin:1rem 0">
                {features_html}
                <div style="height:1.5rem"></div>
            </div>
            """, unsafe_allow_html=True)

            if is_current:
                st.button(
                    f"{plan['icon']} Current plan",
                    key=f"plan_btn_{plan['key']}",
                    use_container_width=True,
                    disabled=True,
                )
            elif plan["key"] == "free":
                st.button(
                    "Downgrade to Free",
                    key=f"plan_btn_{plan['key']}",
                    use_container_width=True,
                )
            else:
                if st.button(
                    f"Upgrade to {plan['name']}  →",
                    key=f"plan_btn_{plan['key']}",
                    use_container_width=True,
                    type="primary" if is_popular else "secondary",
                ):
                    _upgrade(plan["key"])

    # ── comparison table ──────────────────────────────────────
    st.markdown("<div style='height:2.5rem'></div>", unsafe_allow_html=True)
    st.markdown("""
    <div class="page-header" style="margin-top:1rem">
        <div class="page-title" style="font-size:1.375rem">Full comparison</div>
    </div>
    """, unsafe_allow_html=True)

    import pandas as pd
    rows = []
    for feat, _ in PLANS[0]["features"]:
        row = {"Feature": feat}
        for plan in PLANS:
            feat_map = {f: ok for f, ok in plan["features"]}
            row[plan["name"]] = "✓" if feat_map.get(feat, False) else "—"
        rows.append(row)

    df = pd.DataFrame(rows)
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        height=320,
    )

    # ── FAQ ───────────────────────────────────────────────────
    st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)
    st.markdown('<div class="page-title" style="font-size:1.25rem;margin-bottom:1rem">FAQ</div>',
                unsafe_allow_html=True)

    faqs = [
        ("Can I cancel anytime?",
         "Yes. Canceling stops your next billing cycle; you keep access until it ends."),
        ("What happens when I hit the token limit?",
         "Requests are rate-limited until the next billing period, or you can upgrade."),
        ("Is there a free trial for Pro?",
         "New Pro subscribers get a 7-day free trial automatically."),
        ("Do unused tokens roll over?",
         "No, token quotas reset on the first day of each billing cycle."),
    ]
    for q, a in faqs:
        with st.expander(q):
            st.markdown(
                f'<span style="color:var(--text-secondary);font-size:0.9rem">{a}</span>',
                unsafe_allow_html=True
            )
