"""
frontend/pages/admin_page.py — Claude-style Admin Dashboard
============================================================
Correct endpoints:
  GET  /api/v1/admin/users                  → AdminUserListResponse
  POST /api/v1/admin/users/{id}/action      → { message }
  GET  /api/v1/admin/metrics/usage          → AdminUsageMetrics
  GET  /api/v1/admin/metrics/subscriptions  → AdminSubscriptionMetrics
  GET  /api/v1/admin/health                 → SystemHealthResponse
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

BASE = settings.BACKEND_URL


# ── API helpers ──────────────────────────────────────────────────────────
def _get(path: str, params: dict = None):
    try:
        r = requests.get(
            f"{BASE}{path}",
            headers=get_auth_headers(),
            params=params,
            timeout=10,
        )
        return r.json() if r.ok else None
    except Exception:
        return None


def _post(path: str, payload: dict):
    try:
        r = requests.post(
            f"{BASE}{path}",
            headers=get_auth_headers(),
            json=payload,
            timeout=10,
        )
        if r.ok:
            return True, r.json().get("message", "Done")
        return False, r.json().get("detail", "Failed")
    except Exception as exc:
        return False, str(exc)


def _fmt(iso: str) -> str:
    try:
        return datetime.fromisoformat(
            iso.replace("Z", "+00:00")
        ).strftime("%b %d, %Y")
    except Exception:
        return (iso or "")[:10] or "—"


def _big(n: int) -> str:
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.1f}K"
    return str(n)


# ── reusable card HTML ───────────────────────────────────────────────────
def _kpi(icon: str, label: str, value: str, sub: str, accent: str) -> str:
    return f"""
    <div style="background:rgba(255,255,255,0.035);
                border:1px solid rgba(255,255,255,0.08);
                border-radius:16px;padding:20px 22px;
                position:relative;overflow:hidden;
                transition:all .25s ease">
      <div style="position:absolute;top:0;left:0;right:0;height:3px;
                  background:linear-gradient(90deg,{accent}cc,{accent}44)"></div>
      <div style="font-size:1.5rem;margin-bottom:10px">{icon}</div>
      <div style="font-size:2rem;font-weight:800;color:#f1f5f9;
                  letter-spacing:-0.03em;line-height:1">{value}</div>
      <div style="font-size:0.72rem;font-weight:700;color:#64748b;
                  text-transform:uppercase;letter-spacing:.08em;
                  margin-top:5px">{label}</div>
      <div style="font-size:0.78rem;color:#94a3b8;margin-top:3px">{sub}</div>
    </div>"""


# ── main ─────────────────────────────────────────────────────────────────
def render_admin_page() -> None:

    # guard
    if st.session_state.get("user_role") != "admin":
        st.markdown("""
        <div style="text-align:center;padding:6rem 1rem">
          <div style="font-size:3.5rem;margin-bottom:12px">🔒</div>
          <div style="font-size:1.5rem;font-weight:700;color:#fca5a5">
            Access Denied
          </div>
          <div style="color:#64748b;margin-top:8px">
            You need administrator privileges to view this page.
          </div>
        </div>""", unsafe_allow_html=True)
        return

    # ── header bar ───────────────────────────────────────────
    st.markdown("""
    <div style="display:flex;align-items:center;justify-content:space-between;
                padding-bottom:20px;border-bottom:1px solid rgba(255,255,255,0.07);
                margin-bottom:24px;flex-wrap:wrap;gap:10px">
      <div>
        <div style="font-size:1.625rem;font-weight:800;color:#f1f5f9;
                    letter-spacing:-0.03em">🛡️ Admin Dashboard</div>
        <div style="font-size:0.875rem;color:#64748b;margin-top:3px">
          System overview, user management &amp; analytics
        </div>
      </div>
      <span style="background:rgba(99,102,241,0.18);color:#a5b4fc;
                   border:1px solid rgba(99,102,241,0.3);border-radius:99px;
                   font-size:0.72rem;font-weight:700;padding:4px 12px;
                   text-transform:uppercase;letter-spacing:.06em">Administrator</span>
    </div>
    """, unsafe_allow_html=True)

    # ── fetch all data ────────────────────────────────────────
    usage  = _get("/api/v1/admin/metrics/usage")   or {}
    subs   = _get("/api/v1/admin/metrics/subscriptions") or {}
    health = _get("/api/v1/admin/health")          or {}

    total_users   = usage.get("total_users", 0)
    active_today  = usage.get("active_users_today", 0)
    req_today     = usage.get("total_requests_today", 0)
    tok_today     = usage.get("total_tokens_today", 0)
    cost_today    = usage.get("estimated_cost_today_usd", 0.0)
    req_month     = usage.get("total_requests_month", 0)
    tok_month     = usage.get("total_tokens_month", 0)
    cost_month    = usage.get("estimated_cost_month_usd", 0.0)
    errors_today  = usage.get("errors_today", 0)
    blocks_today  = usage.get("guardrail_blocks_today", 0)
    by_feature    = usage.get("requests_by_feature", {})

    free_cnt  = subs.get("free_count",       0)
    pro_cnt   = subs.get("pro_count",        0)
    ent_cnt   = subs.get("enterprise_count", 0)
    revenue   = subs.get("monthly_revenue_usd", 0.0)

    # ── KPI row ───────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4, gap="small")
    with c1:
        st.markdown(_kpi("👥","Total Users", _big(total_users),
                         f"{active_today} active today","#6366f1"),
                    unsafe_allow_html=True)
    with c2:
        st.markdown(_kpi("⚡","Tokens Today", _big(tok_today),
                         f"{_big(tok_month)} this month","#06b6d4"),
                    unsafe_allow_html=True)
    with c3:
        st.markdown(_kpi("💬","Requests Today", _big(req_today),
                         f"{_big(req_month)} this month","#10b981"),
                    unsafe_allow_html=True)
    with c4:
        st.markdown(_kpi("💰","Est. Revenue", f"${revenue:,.0f}",
                         f"${cost_month:.2f} in API cost","#f59e0b"),
                    unsafe_allow_html=True)

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    # ── second row: plan breakdown + health + feature dist ───
    row2_l, row2_m, row2_r = st.columns([2, 2, 2], gap="small")

    with row2_l:
        st.markdown("""
        <div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.08);
                    border-radius:16px;padding:20px 22px;height:100%">
          <div style="font-size:0.78rem;font-weight:700;color:#64748b;
                      text-transform:uppercase;letter-spacing:.08em;
                      margin-bottom:16px">Subscription Breakdown</div>
        """, unsafe_allow_html=True)

        for plan_name, count, color, icon in [
            ("Free",       free_cnt, "#94a3b8", "✦"),
            ("Pro",        pro_cnt,  "#6366f1", "⚡"),
            ("Enterprise", ent_cnt,  "#06b6d4", "🚀"),
        ]:
            total_subs = max(free_cnt + pro_cnt + ent_cnt, 1)
            pct = count / total_subs * 100
            st.markdown(f"""
            <div style="margin-bottom:14px">
              <div style="display:flex;justify-content:space-between;
                          font-size:0.83rem;margin-bottom:5px">
                <span style="color:#e2e8f0;font-weight:600">{icon} {plan_name}</span>
                <span style="color:#94a3b8">{count} users</span>
              </div>
              <div style="background:rgba(255,255,255,0.06);
                          border-radius:99px;height:6px;overflow:hidden">
                <div style="width:{pct:.0f}%;background:{color};
                            border-radius:99px;height:6px"></div>
              </div>
            </div>
            """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with row2_m:
        sys_status = health.get("status", "unknown")
        sys_color  = {"healthy":"#10b981","degraded":"#f59e0b",
                      "unhealthy":"#ef4444"}.get(sys_status,"#94a3b8")
        db_info    = health.get("database", {})
        redis_info = health.get("redis", {})

        st.markdown(f"""
        <div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.08);
                    border-radius:16px;padding:20px 22px;height:100%">
          <div style="font-size:0.78rem;font-weight:700;color:#64748b;
                      text-transform:uppercase;letter-spacing:.08em;
                      margin-bottom:14px">System Health</div>

          <div style="display:flex;align-items:center;gap:8px;margin-bottom:16px">
            <div style="width:10px;height:10px;border-radius:50%;
                        background:{sys_color};
                        box-shadow:0 0 8px {sys_color}88"></div>
            <span style="font-weight:700;color:{sys_color};
                         text-transform:capitalize;font-size:0.9375rem">
              {sys_status}
            </span>
            <span style="color:#64748b;font-size:0.78rem">
              v{health.get("version","0.1.0")}
            </span>
          </div>
        """, unsafe_allow_html=True)

        for svc_name, info, icon in [
            ("Database", db_info, "🗄️"),
            ("Redis",    redis_info, "⚡"),
        ]:
            ok      = info.get("status") == "ok"
            latency = info.get("latency_ms", 0)
            dot_col = "#10b981" if ok else "#ef4444"
            st.markdown(f"""
            <div style="display:flex;align-items:center;justify-content:space-between;
                        padding:10px 14px;background:rgba(255,255,255,0.03);
                        border-radius:10px;margin-bottom:8px">
              <div style="display:flex;align-items:center;gap:8px">
                <span>{icon}</span>
                <span style="color:#e2e8f0;font-size:0.875rem;font-weight:600">
                  {svc_name}
                </span>
              </div>
              <div style="display:flex;align-items:center;gap:8px">
                <span style="color:#94a3b8;font-size:0.78rem">{latency}ms</span>
                <div style="width:8px;height:8px;border-radius:50%;
                            background:{dot_col}"></div>
              </div>
            </div>
            """, unsafe_allow_html=True)

        # errors / blocks
        st.markdown(f"""
        <div style="display:flex;gap:8px;margin-top:4px">
          <div style="flex:1;background:rgba(239,68,68,0.08);
                      border:1px solid rgba(239,68,68,0.2);
                      border-radius:10px;padding:10px;text-align:center">
            <div style="font-size:1.25rem;font-weight:800;color:#fca5a5">
              {errors_today}
            </div>
            <div style="font-size:0.7rem;color:#94a3b8;margin-top:2px">
              Errors today
            </div>
          </div>
          <div style="flex:1;background:rgba(245,158,11,0.08);
                      border:1px solid rgba(245,158,11,0.2);
                      border-radius:10px;padding:10px;text-align:center">
            <div style="font-size:1.25rem;font-weight:800;color:#fcd34d">
              {blocks_today}
            </div>
            <div style="font-size:0.7rem;color:#94a3b8;margin-top:2px">
              Guardrail blocks
            </div>
          </div>
        </div>
        </div>
        """, unsafe_allow_html=True)

    with row2_r:
        st.markdown("""
        <div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.08);
                    border-radius:16px;padding:20px 22px;height:100%">
          <div style="font-size:0.78rem;font-weight:700;color:#64748b;
                      text-transform:uppercase;letter-spacing:.08em;
                      margin-bottom:16px">Requests by Feature</div>
        """, unsafe_allow_html=True)

        feature_cfg = {
            "chat":      ("💬", "#6366f1"),
            "rag":       ("🔍", "#06b6d4"),
            "agent":     ("🤖", "#10b981"),
            "tool_call": ("🔧", "#f59e0b"),
        }
        total_feat = max(sum(by_feature.values()), 1)
        for key, (icon, color) in feature_cfg.items():
            cnt = by_feature.get(key, 0)
            pct = cnt / total_feat * 100
            st.markdown(f"""
            <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px">
              <span style="font-size:1rem;width:24px;text-align:center">{icon}</span>
              <div style="flex:1">
                <div style="display:flex;justify-content:space-between;
                            font-size:0.8rem;margin-bottom:4px">
                  <span style="color:#e2e8f0;font-weight:500">
                    {key.replace("_"," ").title()}
                  </span>
                  <span style="color:#64748b">{cnt}</span>
                </div>
                <div style="background:rgba(255,255,255,0.06);
                            border-radius:99px;height:5px;overflow:hidden">
                  <div style="width:{pct:.0f}%;background:{color};
                              border-radius:99px;height:5px"></div>
                </div>
              </div>
            </div>
            """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)

    # ── User Management ───────────────────────────────────────
    st.markdown("""
    <div style="font-size:1.125rem;font-weight:700;color:#f1f5f9;
                margin-bottom:14px;letter-spacing:-0.02em">
      👥 User Management
    </div>
    """, unsafe_allow_html=True)

    # search / filter toolbar
    col_s, col_r, col_f, col_btn = st.columns([3, 2, 2, 1])
    with col_s:
        search = st.text_input("Search", placeholder="Name or email…",
                               key="adm_search", label_visibility="collapsed")
    with col_r:
        role_f = st.selectbox("Role", ["All", "user", "admin"],
                              key="adm_role", label_visibility="collapsed")
    with col_f:
        page_n = st.number_input("Page", min_value=1, value=1,
                                  key="adm_page", label_visibility="collapsed")
    with col_btn:
        if st.button("↻", use_container_width=True, key="adm_refresh"):
            st.rerun()

    params = {"page": page_n, "page_size": 20}
    if search:
        params["search"] = search

    users_data = _get("/api/v1/admin/users", params) or {}
    users: list = users_data.get("users", [])
    total_u = users_data.get("total", 0)
    pg_size = users_data.get("page_size", 20)

    if role_f != "All":
        users = [u for u in users if u.get("role", "").lower() == role_f.lower()]

    st.markdown(
        f'<div style="font-size:0.78rem;color:#64748b;margin-bottom:10px">'
        f'Showing {len(users)} of {total_u} users'
        f'</div>',
        unsafe_allow_html=True
    )

    if users:
        # header
        st.markdown("""
        <div style="display:grid;grid-template-columns:2fr 1fr 1fr 1fr 1fr 80px;
                    gap:8px;padding:8px 16px;
                    border-bottom:1px solid rgba(255,255,255,0.07);
                    font-size:0.72rem;font-weight:700;color:#64748b;
                    text-transform:uppercase;letter-spacing:.07em">
          <div>User</div><div>Role</div><div>Status</div>
          <div>Plan</div><div>Tokens</div><div>Action</div>
        </div>
        """, unsafe_allow_html=True)

        for u in users:
            uid        = str(u.get("id", ""))
            name       = u.get("full_name", "Unknown")
            email      = u.get("email", "")
            role_v     = u.get("role", "user")
            active     = u.get("is_active", True)
            plan_v     = u.get("subscription_plan") or "free"
            tokens_v   = u.get("total_tokens_used", 0)
            joined     = _fmt(str(u.get("created_at", "")))
            initials   = name[:2].upper()

            role_badge = (
                '<span style="background:rgba(99,102,241,0.18);color:#a5b4fc;'
                'border:1px solid rgba(99,102,241,0.3);border-radius:99px;'
                'font-size:0.7rem;font-weight:700;padding:2px 8px">Admin</span>'
                if role_v == "admin" else
                '<span style="background:rgba(59,130,246,0.15);color:#93c5fd;'
                'border:1px solid rgba(59,130,246,0.3);border-radius:99px;'
                'font-size:0.7rem;font-weight:700;padding:2px 8px">User</span>'
            )
            status_badge = (
                '<span style="background:rgba(16,185,129,0.12);color:#6ee7b7;'
                'border:1px solid rgba(16,185,129,0.3);border-radius:99px;'
                'font-size:0.7rem;font-weight:700;padding:2px 8px">Active</span>'
                if active else
                '<span style="background:rgba(239,68,68,0.12);color:#fca5a5;'
                'border:1px solid rgba(239,68,68,0.3);border-radius:99px;'
                'font-size:0.7rem;font-weight:700;padding:2px 8px">Disabled</span>'
            )
            plan_colors = {"pro":"#6366f1","enterprise":"#06b6d4","free":"#94a3b8"}
            plan_badge = (
                f'<span style="color:{plan_colors.get(plan_v,"#94a3b8")};'
                f'font-size:0.78rem;font-weight:600">{plan_v.title()}</span>'
            )

            col_u, col_act = st.columns([11, 1])
            with col_u:
                st.markdown(f"""
                <div style="display:grid;
                            grid-template-columns:2fr 1fr 1fr 1fr 1fr 80px;
                            gap:8px;padding:12px 16px;align-items:center;
                            border-bottom:1px solid rgba(255,255,255,0.04)">
                  <div style="display:flex;align-items:center;gap:10px">
                    <div style="width:32px;height:32px;border-radius:50%;
                                background:linear-gradient(135deg,#6366f1,#06b6d4);
                                display:flex;align-items:center;justify-content:center;
                                font-size:0.8rem;font-weight:700;color:white;
                                flex-shrink:0">{initials}</div>
                    <div style="min-width:0">
                      <div style="font-weight:600;color:#f1f5f9;font-size:0.875rem;
                                  white-space:nowrap;overflow:hidden;text-overflow:ellipsis">
                        {name}
                      </div>
                      <div style="font-size:0.73rem;color:#64748b">{email}</div>
                    </div>
                  </div>
                  <div>{role_badge}</div>
                  <div>{status_badge}</div>
                  <div>{plan_badge}</div>
                  <div style="font-size:0.83rem;color:#94a3b8">{_big(tokens_v)}</div>
                  <div></div>
                </div>
                """, unsafe_allow_html=True)
            with col_act:
                action_map = {
                    "Disable":       "disable",
                    "Enable":        "enable",
                    "Make Admin":    "promote",
                    "Revoke Admin":  "demote",
                }
                chosen = st.selectbox("", list(action_map.keys()),
                                      key=f"act_{uid}",
                                      label_visibility="collapsed")
                if st.button("▶", key=f"go_{uid}",
                             use_container_width=True,
                             help=f"Apply: {chosen}"):
                    ok, msg = _post(
                        f"/api/v1/admin/users/{uid}/action",
                        {"action": action_map[chosen]}
                    )
                    if ok:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)

    else:
        st.markdown("""
        <div style="text-align:center;padding:3rem;color:#64748b">
          No users found matching your criteria.
        </div>""", unsafe_allow_html=True)

    # pagination
    if total_u > pg_size:
        max_pages = (total_u + pg_size - 1) // pg_size
        st.markdown(
            f'<div style="text-align:center;font-size:0.8rem;color:#64748b;'
            f'margin-top:12px">Page {page_n} of {max_pages}</div>',
            unsafe_allow_html=True
        )
