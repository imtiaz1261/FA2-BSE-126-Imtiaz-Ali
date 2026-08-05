"""
Premium Usage & Billing Dashboard — Phase 15.
Quota gauge, plan comparison, daily charts, upgrade flow.
"""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from api_client.client import api_client
from state.session import is_authenticated
from theme import inject_global_css, inject_page_bg
from ui_components import kpi_card, plan_badge, section_header

st.set_page_config(page_title="Usage & Billing", page_icon="📊",
                   layout="wide", initial_sidebar_state="collapsed")
inject_global_css()
inject_page_bg()

if not is_authenticated():
    st.error("Please log in first.")
    st.stop()

token = st.session_state["access_token"]
user  = st.session_state.get("user", {})

_C = {"blue":"#4f8ef7","green":"#22c55e","amber":"#f59e0b",
      "red":"#ef4444","purple":"#8b5cf6","teal":"#14b8a6"}

_CHART = dict(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font_color="#94a3b8",
    xaxis=dict(gridcolor="#1e2d47", color="#64748b"),
    yaxis=dict(gridcolor="#1e2d47", color="#64748b"),
    margin=dict(t=10,b=10,l=0,r=0),
)


@st.cache_data(ttl=60, show_spinner=False)
def _load(tok):
    return api_client.get_my_usage(tok)


result = _load(token)
if not result.ok:
    st.error(f"Failed to load usage: {result.error}")
    st.stop()

d   = result.data
pln = d.get("plan_label","Free")
used = d.get("monthly_used",0)
lim  = d.get("monthly_limit",100)
rem  = d.get("monthly_remaining",0)
pct  = d.get("quota_percent",0.0)
tok_ = d.get("tokens_used",0)
cost = d.get("cost_usd",0.0)

# ── Page header ───────────────────────────────────────────────────────────────
col_h1, col_h2 = st.columns([4,1])
with col_h1:
    st.markdown(
        f'<div style="margin-bottom:24px;">'
        f'<h1 style="color:#f0f4ff;font-size:1.7rem;font-weight:700;margin:0;">Usage & Billing</h1>'
        f'<p style="color:#64748b;margin:4px 0 0;font-size:0.88rem;">'
        f'Monitor your AI usage, costs, and subscription plan.</p>'
        f'</div>',
        unsafe_allow_html=True,
    )
with col_h2:
    st.markdown(
        f'<div style="text-align:right;padding-top:8px;">'
        + plan_badge(d.get("plan","free"), size="lg") +
        '</div>',
        unsafe_allow_html=True,
    )

# ── KPI row ───────────────────────────────────────────────────────────────────
k1,k2,k3,k4 = st.columns(4)
kpi_card("Requests Used",   f"{used:,}", f"of {lim:,} monthly", "📊", col=k1)
kpi_card("Tokens Used",     f"{tok_:,}", "this month",          "⚡", col=k2,
         accent=_C["purple"])
kpi_card("Estimated Cost",  f"${cost:.4f}", "this month",       "💰", col=k3,
         accent=_C["amber"])
kpi_card("Remaining",       f"{rem:,}",   "requests left",      "✅", col=k4,
         accent=_C["green"])

st.markdown("<br>", unsafe_allow_html=True)

# ── Quota gauge + Endpoint pie ────────────────────────────────────────────────
col_g, col_e = st.columns([2,3])

with col_g:
    section_header("Monthly Quota", "", "📈")
    bar_col = _C["green"] if pct < 70 else (_C["amber"] if pct < 90 else _C["red"])
    fig_g = go.Figure(go.Indicator(
        mode="gauge+number",
        value=pct,
        number={"suffix":"%","font":{"color":"#f0f4ff","size":32}},
        gauge={
            "axis":       {"range":[0,100],"tickcolor":"#1e2d47"},
            "bar":        {"color": bar_col},
            "bgcolor":    "#0f1629",
            "bordercolor":"#1e2d47",
            "steps": [
                {"range":[0,70],  "color":"#131d32"},
                {"range":[70,90], "color":"#1c1810"},
                {"range":[90,100],"color":"#1c1010"},
            ],
            "threshold":{"line":{"color":_C["red"],"width":2},"value":90},
        },
        title={"text":f"{rem:,} requests remaining","font":{"color":"#64748b","size":13}},
    ))
    fig_g.update_layout(paper_bgcolor="rgba(0,0,0,0)",font_color="#94a3b8",
                        margin=dict(t=30,b=10,l=20,r=20),height=250)
    st.plotly_chart(fig_g, use_container_width=True)

    period_end = d.get("period_end","")[:10]
    st.markdown(
        f'<div style="text-align:center;color:#4a5568;font-size:0.78rem;">'
        f'Resets: {period_end}</div>',
        unsafe_allow_html=True,
    )

    if d.get("plan","free") == "free":
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("⚡ Upgrade to Pro", type="primary", use_container_width=True):
            res = api_client.upgrade_plan(token,"pro")
            if res.ok:
                st.success("✅ Upgraded to Pro!")
                st.cache_data.clear()
                st.rerun()
            else:
                st.error(res.error)

with col_e:
    section_header("Usage by Feature", "", "🎯")
    by_ep = d.get("by_endpoint",[])
    if by_ep:
        df_ep = pd.DataFrame(by_ep)
        fig_pie = px.pie(df_ep, values="calls", names="endpoint", hole=0.45,
                         color_discrete_sequence=list(_C.values()))
        fig_pie.update_layout(**{**_CHART, "legend":dict(font=dict(color="#94a3b8")),
                                 "height":280})
        fig_pie.update_traces(textfont_color="#f0f4ff",
                               hovertemplate="%{label}<br>%{value} calls (%{percent})")
        st.plotly_chart(fig_pie, use_container_width=True)

        df_ep2 = df_ep[["endpoint","calls","tokens","cost"]].rename(columns={
            "endpoint":"Feature","calls":"Calls","tokens":"Tokens","cost":"Cost $"
        })
        df_ep2["Cost $"] = df_ep2["Cost $"].apply(lambda x: f"${x:.4f}")
        st.dataframe(df_ep2, use_container_width=True, hide_index=True)
    else:
        st.markdown(
            '<div style="color:#4a5568;font-size:0.88rem;text-align:center;padding:40px;">'
            'No usage data yet</div>',
            unsafe_allow_html=True,
        )

# ── Daily usage chart ─────────────────────────────────────────────────────────
st.divider()
section_header("Daily Activity", f"Last 30 days", "📅")
daily = d.get("daily_usage",[])
if daily:
    df = pd.DataFrame(daily)
    df["day"] = pd.to_datetime(df["day"])
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df["day"],y=df["calls"],name="Requests",
                         marker_color=_C["blue"],opacity=0.8))
    fig.add_trace(go.Scatter(x=df["day"],y=df["cost"],name="Cost ($)",
                             yaxis="y2",mode="lines+markers",
                             line=dict(color=_C["amber"],width=2),marker=dict(size=5)))
    fig.update_layout(
        **_CHART,
        yaxis2=dict(overlaying="y",side="right",title="Cost USD",
                    gridcolor="rgba(0,0,0,0)",color="#64748b"),
        legend=dict(font=dict(color="#94a3b8"),bgcolor="rgba(0,0,0,0)"),
        hovermode="x unified",height=280,
        yaxis=dict(gridcolor="#1e2d47",color="#64748b",title="Requests"),
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No activity yet this month.")

# ── Plan comparison table ─────────────────────────────────────────────────────
st.divider()
section_header("Plan Comparison", "Choose the right plan for your needs", "💎")

plans = [
    ("",         "Free",          "Pro",           "Enterprise"),
    ("Price",    "$0/month",      "$19/month",      "$99/month"),
    ("Requests", "100/month",     "2,000/month",    "50,000/month"),
    ("Documents","5",             "100",            "1,000"),
    ("Chat",     "✅",            "✅",             "✅"),
    ("RAG",      "✅",            "✅",             "✅"),
    ("Research", "❌",            "✅",             "✅"),
    ("Agents",   "❌",            "✅",             "✅"),
    ("Support",  "Community",     "Email",          "Dedicated"),
]
df_plans = pd.DataFrame(plans[1:], columns=plans[0])
st.dataframe(df_plans, use_container_width=True, hide_index=True)
