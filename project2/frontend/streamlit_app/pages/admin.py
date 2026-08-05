"""
Premium Admin Dashboard — Enterprise Analytics.
Phase 18: Users, AI Usage, Growth, Cost, Security.
"""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
from api_client.client import api_client
from state.session import is_authenticated
from theme import inject_global_css, inject_page_bg
from ui_components import kpi_card, plan_badge, status_badge, section_header

st.set_page_config(page_title="Admin Dashboard", page_icon="🛡️",
                   layout="wide", initial_sidebar_state="collapsed")
inject_global_css()
inject_page_bg()

if not is_authenticated():
    st.error("Please log in first.")
    st.stop()
user = st.session_state.get("user",{})
if not user.get("is_admin",False):
    st.error("🚫 Admin access required.")
    st.stop()

token = st.session_state["access_token"]

_C = {"blue":"#4f8ef7","green":"#22c55e","amber":"#f59e0b",
      "red":"#ef4444","purple":"#8b5cf6","teal":"#14b8a6","cyan":"#06b6d4"}
_CHART_THEME = dict(
    paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",
    font_color="#94a3b8",
    margin=dict(t=10,b=10,l=0,r=0),
)

def _ax(): return dict(gridcolor="#1e2d47",color="#64748b",zeroline=False)


def _fmt(n):
    if n is None: return "—"
    n = int(n)
    if n>=1_000_000: return f"{n/1_000_000:.1f}M"
    if n>=1_000: return f"{n/1_000:.1f}K"
    return str(n)

def _fmtc(c):
    if c is None: return "—"
    c=float(c)
    return f"${c:.2f}" if c>=1 else f"${c:.4f}"


@st.cache_data(ttl=120, show_spinner=False)
def _stats(tok,d): return api_client.admin_get_stats(tok,days=d)
@st.cache_data(ttl=120, show_spinner=False)
def _daily(tok,d): return api_client.admin_daily_usage(tok,days=d)
@st.cache_data(ttl=120, show_spinner=False)
def _ep(tok,d): return api_client.admin_endpoint_breakdown(tok,days=d)
@st.cache_data(ttl=120, show_spinner=False)
def _top(tok,d): return api_client.admin_top_users(tok,days=d,limit=15)
@st.cache_data(ttl=120, show_spinner=False)
def _sigs(tok,d): return api_client.admin_daily_new_users(tok,days=d)
@st.cache_data(ttl=60,  show_spinner=False)
def _users(tok): return api_client.admin_list_users(tok,limit=200)
@st.cache_data(ttl=120, show_spinner=False)
def _sec_sum(tok,d): return api_client.admin_security_summary(tok,days=d)
@st.cache_data(ttl=60,  show_spinner=False)
def _sec_evt(tok): return api_client.admin_security_events(tok,limit=50)
@st.cache_data(ttl=120, show_spinner=False)
def _sec_daily(tok,d): return api_client.admin_security_daily(tok,days=d)


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        '<div style="padding:20px 16px 12px;border-bottom:1px solid #1e2d47;">'
        '<div style="color:#f0f4ff;font-size:1rem;font-weight:700;">🛡️ Admin</div>'
        '<div style="color:#4a5568;font-size:0.72rem;">Platform Analytics</div>'
        '</div>',
        unsafe_allow_html=True,
    )
    days = st.select_slider("Window",options=[7,14,30,60,90,180,365],value=30,
                            label_visibility="collapsed")
    st.caption(f"Last **{days}** days")
    st.divider()
    section = st.radio("Section",[
        "📊  Overview","🤖  AI Usage","👥  User Growth",
        "💰  Cost Report","🔧  User Manager","🔒  Security"
    ],label_visibility="collapsed")
    st.divider()
    if st.button("← Back to App", use_container_width=True):
        st.switch_page("app.py")

# helper: themed chart layout
def _layout(**kw):
    d = {**_CHART_THEME,
         "xaxis":_ax(),"yaxis":_ax(),
         "legend":dict(font=dict(color="#94a3b8"),bgcolor="rgba(0,0,0,0)")}
    d.update(kw)
    return d


# ============================================================================
# OVERVIEW
# ============================================================================
if "Overview" in section:
    section_header("Platform Overview",
                   f"Real-time analytics · last {days} days","📊")
    sr = _stats(token,days)
    if not sr.ok:
        st.error(sr.error); st.stop()
    s = sr.data

    k1,k2,k3,k4 = st.columns(4)
    kpi_card("Total Users",   _fmt(s["total_users"]),
             f"+{s['new_users']} new","👥", col=k1)
    kpi_card("Active Users",  _fmt(s["active_users"]),
             f"of {_fmt(s['total_users'])} total","✅",col=k2,accent=_C["green"])
    kpi_card("LLM Calls",     _fmt(s["total_calls"]),
             f"last {days}d","⚡",col=k3,accent=_C["purple"])
    kpi_card("Total Cost",    _fmtc(s["total_cost_usd"]),
             f"{_fmt(s['total_tokens'])} tokens","💰",col=k4,accent=_C["amber"])

    st.markdown("<br>",unsafe_allow_html=True)
    cl,cr = st.columns(2)

    with cl:
        section_header("Plan Distribution","","🥧")
        pc = s.get("plan_counts",{})
        if any(v>0 for v in pc.values()):
            df_p = pd.DataFrame([{"Plan":k.title(),"Users":v} for k,v in pc.items() if v>0])
            fig = px.pie(df_p,values="Users",names="Plan",hole=0.48,
                         color_discrete_sequence=list(_C.values()))
            fig.update_layout(**_layout(height=260))
            fig.update_traces(textfont_color="#f0f4ff")
            st.plotly_chart(fig,use_container_width=True)

    with cr:
        section_header("Daily Calls","Last 14 days","📈")
        dr = _daily(token,min(days,14))
        if dr.ok and dr.data:
            df = pd.DataFrame(dr.data)
            df["day"] = pd.to_datetime(df["day"])
            fig2 = px.bar(df,x="day",y="calls",
                          color_discrete_sequence=[_C["blue"]])
            fig2.update_layout(**_layout(height=260))
            st.plotly_chart(fig2,use_container_width=True)


# ============================================================================
# AI USAGE
# ============================================================================
elif "AI Usage" in section:
    section_header("AI Usage Analytics",
                   f"Tokens, cost, and endpoint breakdown · last {days}d","🤖")
    dr  = _daily(token,days)
    epr = _ep(token,days)

    c1,c2 = st.columns([3,1])
    with c1:
        if dr.ok and dr.data:
            df = pd.DataFrame(dr.data)
            df["day"] = pd.to_datetime(df["day"])
            fig = make_subplots(specs=[[{"secondary_y":True}]])
            fig.add_trace(go.Bar(x=df["day"],y=df["tokens"],name="Tokens",
                                 marker_color=_C["blue"],opacity=0.8),secondary_y=False)
            fig.add_trace(go.Scatter(x=df["day"],y=df["cost"],name="Cost ($)",
                                     mode="lines+markers",
                                     line=dict(color=_C["amber"],width=2)),secondary_y=True)
            fig.update_layout(**_layout(hovermode="x unified",height=300,
                                        yaxis=dict(**_ax(),title="Tokens"),
                                        yaxis2=dict(title="Cost USD",**_ax())))
            st.plotly_chart(fig,use_container_width=True)

            df["cumcost"] = df["cost"].cumsum()
            figc = px.area(df,x="day",y="cumcost",color_discrete_sequence=[_C["teal"]],
                           labels={"cumcost":"Cumulative Cost (USD)"})
            figc.update_layout(**_layout(height=200))
            st.plotly_chart(figc,use_container_width=True)
        else:
            st.info("No usage data yet.")

    with c2:
        if epr.ok and epr.data:
            df_ep = pd.DataFrame(epr.data)
            figp = px.pie(df_ep,values="tokens",names="endpoint",hole=0.42,
                          color_discrete_sequence=list(_C.values()))
            figp.update_layout(**_layout(height=260))
            figp.update_traces(textfont_color="#f0f4ff")
            st.plotly_chart(figp,use_container_width=True)
            st.dataframe(
                df_ep[["endpoint","calls","tokens","cost"]].rename(columns={
                    "endpoint":"Feature","calls":"Calls",
                    "tokens":"Tokens","cost":"Cost $"}),
                use_container_width=True,hide_index=True,
            )


# ============================================================================
# USER GROWTH
# ============================================================================
elif "User Growth" in section:
    section_header("User Growth",f"Registrations and plan distribution","👥")
    sr   = _stats(token,days)
    sigr = _sigs(token,days)

    if sr.ok:
        s=sr.data
        k1,k2,k3=st.columns(3)
        kpi_card("Total Users", _fmt(s["total_users"]),col=k1)
        kpi_card("Active Users",_fmt(s["active_users"]),f"used AI in {days}d",
                 col=k2,accent=_C["green"])
        kpi_card("New Users",   _fmt(s["new_users"]),f"last {days}d",
                 col=k3,accent=_C["cyan"])

    st.markdown("<br>",unsafe_allow_html=True)
    cl,cr=st.columns([3,2])

    with cl:
        section_header("Daily Registrations","7-day rolling average","📅")
        if sigr.ok and sigr.data:
            df_s=pd.DataFrame(sigr.data)
            df_s["day"]=pd.to_datetime(df_s["day"])
            df_s["roll"]=df_s["count"].rolling(7,min_periods=1).mean()
            fig=go.Figure()
            fig.add_trace(go.Bar(x=df_s["day"],y=df_s["count"],name="Signups",
                                 marker_color=_C["blue"],opacity=0.7))
            fig.add_trace(go.Scatter(x=df_s["day"],y=df_s["roll"],name="7-day avg",
                                     line=dict(color=_C["amber"],width=2,dash="dot")))
            fig.update_layout(**_layout(hovermode="x unified",height=280))
            st.plotly_chart(fig,use_container_width=True)

    with cr:
        if sr.ok:
            pc=sr.data.get("plan_counts",{})
            if any(v>0 for v in pc.values()):
                df_p=pd.DataFrame([{"Plan":k.title(),"Users":v}
                                    for k,v in pc.items() if v>0])
                figd=px.pie(df_p,values="Users",names="Plan",hole=0.5,
                            color_discrete_sequence=list(_C.values()))
                figd.update_layout(**_layout(height=260))
                figd.update_traces(textfont_color="#f0f4ff")
                st.plotly_chart(figd,use_container_width=True)

        if sigr.ok and sigr.data:
            df_s2=pd.DataFrame(sigr.data)
            df_s2["day"]=pd.to_datetime(df_s2["day"])
            df_s2["cum"]=df_s2["count"].cumsum()
            figcum=px.area(df_s2,x="day",y="cum",
                           color_discrete_sequence=[_C["purple"]],
                           labels={"cum":"Total Users"})
            figcum.update_layout(**_layout(height=200))
            st.plotly_chart(figcum,use_container_width=True)


# ============================================================================
# COST REPORT
# ============================================================================
elif "Cost Report" in section:
    section_header("Cost Report",f"Spending analysis · last {days}d","💰")
    sr  = _stats(token,days)
    dr  = _daily(token,days)
    tur = _top(token,days)

    if sr.ok:
        s=sr.data
        k1,k2,k3,k4=st.columns(4)
        kpi_card("Total Cost",    _fmtc(s["total_cost_usd"]),f"last {days}d",
                 col=k1,accent=_C["amber"])
        kpi_card("Total Tokens",  _fmt(s["total_tokens"]),f"last {days}d",
                 col=k2,accent=_C["blue"])
        kpi_card("LLM Calls",     _fmt(s["total_calls"]),f"last {days}d",
                 col=k3,accent=_C["purple"])
        avg=s["total_cost_usd"]/max(s["total_calls"],1)
        kpi_card("Avg Cost/Call", _fmtc(avg),"",col=k4,accent=_C["teal"])

    cl,cr=st.columns([3,2])
    with cl:
        if dr.ok and dr.data:
            df=pd.DataFrame(dr.data); df["day"]=pd.to_datetime(df["day"])
            figb=px.bar(df,x="day",y="cost",color_discrete_sequence=[_C["amber"]],
                        labels={"cost":"Cost (USD)"})
            figb.update_layout(**_layout(height=260,
                                         yaxis=dict(**_ax(),tickprefix="$")))
            st.plotly_chart(figb,use_container_width=True)

    with cr:
        if tur.ok and tur.data:
            df_t=pd.DataFrame(tur.data)
            figh=px.bar(df_t.head(10),x="cost",y="email",orientation="h",
                        color="plan",color_discrete_map={
                            "free":_C["blue"],"pro":_C["purple"],
                            "enterprise":_C["amber"]},
                        labels={"cost":"Cost","email":""})
            figh.update_layout(**_layout(height=320,
                                          xaxis=dict(**_ax(),tickprefix="$"),
                                          yaxis=dict(**_ax())))
            st.plotly_chart(figh,use_container_width=True)

    if tur.ok and tur.data:
        st.divider()
        section_header("Top Spenders","","🏆")
        df_tbl=pd.DataFrame(tur.data)[["email","plan","calls","tokens","cost"]]
        df_tbl["cost"]=df_tbl["cost"].apply(lambda x: f"${x:.4f}")
        df_tbl.columns=["Email","Plan","Calls","Tokens","Cost"]
        st.dataframe(df_tbl,use_container_width=True,hide_index=True)


# ============================================================================
# USER MANAGER
# ============================================================================
elif "User Manager" in section:
    section_header("User Manager","Search, filter, and manage all users","🔧")
    ur = _users(token)
    if not ur.ok:
        st.error(ur.error); st.stop()
    users = ur.data or []

    col_s,col_p,col_st = st.columns([3,1,1])
    srch  = col_s.text_input("Search email or name",
                              placeholder="Type to filter…", label_visibility="collapsed")
    p_flt = col_p.selectbox("Plan",["All","Free","Pro","Enterprise"],
                             label_visibility="collapsed")
    s_flt = col_st.selectbox("Status",["All","Active","Inactive"],
                              label_visibility="collapsed")

    flt = users
    if srch:
        q = srch.lower()
        flt=[u for u in flt if q in u["email"].lower() or
             q in (u.get("full_name") or "").lower()]
    if p_flt!="All":
        flt=[u for u in flt if u["plan"].lower()==p_flt.lower()]
    if s_flt!="All":
        flt=[u for u in flt if u["is_active"]==(s_flt=="Active")]

    st.markdown(
        f'<div style="color:#64748b;font-size:0.80rem;margin:8px 0;">'
        f'Showing {len(flt)} of {len(users)} users</div>',
        unsafe_allow_html=True,
    )

    for u in flt:
        is_admin_user = u.get("is_admin",False)
        admin_star    = "🛡️ " if is_admin_user else ""
        status_dot    = "🟢" if u["is_active"] else "🔴"

        with st.expander(
            f"{status_dot} {admin_star}{u['email']}  ·  "
            f"{u['plan'].title()}  ·  "
            f"{u['total_tokens']:,} tokens  ·  ${u['total_cost']:.4f}",
            expanded=False,
        ):
            m1,m2,m3,m4 = st.columns(4)
            m1.metric("Conversations", u["conversations"])
            m2.metric("Documents",     u["documents"])
            m3.metric("Tokens",        f"{u['total_tokens']:,}")
            m4.metric("Cost",          f"${u['total_cost']:.4f}")

            st.caption(
                f"ID: `{u['id']}`  ·  "
                f"Name: {u.get('full_name') or '—'}  ·  "
                f"Joined: {u['created_at'][:10]}"
            )
            b1,b2 = st.columns(2)
            act_lbl = ("🔴 Deactivate" if u["is_active"] else "🟢 Activate")
            if b1.button(act_lbl, key=f"tog_act_{u['id']}", use_container_width=True):
                if u["id"] == str(st.session_state["user"]["id"]):
                    st.warning("Cannot change your own status.")
                else:
                    res = api_client.admin_toggle_active(token,u["id"])
                    if res.ok:
                        _users.clear(); st.rerun()
                    else:
                        st.error(res.error)

            adm_lbl = "Remove Admin" if is_admin_user else "Make Admin"
            if b2.button(adm_lbl, key=f"tog_adm_{u['id']}", use_container_width=True):
                if u["id"] == str(st.session_state["user"]["id"]):
                    st.warning("Cannot change your own admin status.")
                else:
                    res = api_client.admin_toggle_admin(token,u["id"])
                    if res.ok:
                        _users.clear(); st.rerun()
                    else:
                        st.error(res.error)


# ============================================================================
# SECURITY
# ============================================================================
elif "Security" in section:
    section_header("Security Monitor",
                   f"Guardrail events and blocked requests · last {days}d","🔒")
    secr   = _sec_sum(token,days)
    evtr   = _sec_evt(token)
    dailyr = _sec_daily(token,days)

    if secr.ok:
        s=secr.data
        by_cat = s.get("by_category",{})
        by_sev = s.get("by_severity",{})
        top_cat = max(by_cat,key=by_cat.get,default="—") if by_cat else "—"

        k1,k2,k3,k4 = st.columns(4)
        kpi_card("Total Events",  str(s.get("total_events",0)),
                 f"last {days}d","🛡️",col=k1,accent=_C["red"])
        kpi_card("Critical",      str(by_sev.get("critical",0)),
                 "require review","⚠",col=k2,accent=_C["red"])
        kpi_card("Top Category",  top_cat.replace("_"," ").title(),
                 str(by_cat.get(top_cat,0))+" events","🔍",col=k3,accent=_C["amber"])
        kpi_card("High Severity", str(by_sev.get("high",0)),"","⚡",
                 col=k4,accent=_C["amber"])

        st.markdown("<br>",unsafe_allow_html=True)
        cl,cr = st.columns([3,2])

        with cl:
            section_header("Daily Blocked Requests","","📅")
            if dailyr.ok and dailyr.data:
                df_d=pd.DataFrame(dailyr.data)
                df_d["day"]=pd.to_datetime(df_d["day"])
                figdb=px.bar(df_d,x="day",y="count",
                             color_discrete_sequence=[_C["red"]])
                figdb.update_layout(**_layout(height=250))
                st.plotly_chart(figdb,use_container_width=True)

        with cr:
            section_header("By Category","","🥧")
            if by_cat:
                df_cat=pd.DataFrame([{"Category":k.replace("_"," ").title(),"Count":v}
                                      for k,v in by_cat.items()])
                figbc=px.bar(df_cat.sort_values("Count"),x="Count",y="Category",
                             orientation="h",color_discrete_sequence=[_C["amber"]])
                figbc.update_layout(**_layout(height=280,
                                               yaxis=dict(**_ax()),
                                               xaxis=dict(**_ax())))
                st.plotly_chart(figbc,use_container_width=True)

    st.divider()
    section_header("Recent Security Events","","📋")
    if evtr.ok and evtr.data:
        df_ev = pd.DataFrame(evtr.data)[[
            "created_at","category","severity","action","reason","endpoint"
        ]].rename(columns={
            "created_at":"Time","category":"Category","severity":"Severity",
            "action":"Action","reason":"Reason","endpoint":"Endpoint"
        })
        df_ev["Time"]     = df_ev["Time"].str[:16]
        df_ev["Category"] = df_ev["Category"].str.replace("_"," ").str.title()
        st.dataframe(df_ev,use_container_width=True,hide_index=True)
    else:
        st.info("No security events in this window. ✅")
