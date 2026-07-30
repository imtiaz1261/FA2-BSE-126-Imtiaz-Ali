"""
components/agent_panel.py
-------------------------
Displays the real-time multi-agent execution progress panel.

Each agent has one of four states:
  idle    → grey pill  "Waiting…"
  running → green pulse + "Searching…" / "Drafting…" etc.
  done    → green pill  "Complete ✅"
  error   → red pill    "Failed ✗"

The panel reads from st.session_state.agent_statuses which is a list of dicts:
  [{"id": str, "icon": str, "name": str, "status": str, "detail": str}, …]

To connect to a real backend, call set_agent_status() from utils/session.py
inside your generation callback.
"""

from __future__ import annotations

import streamlit as st

from utils.session import reset_agent_statuses


# ──────────────────────────────────────────────────────────────────────────────
# Status → display config
# ──────────────────────────────────────────────────────────────────────────────

_STATUS_CONFIG: dict[str, dict] = {
    "idle":    {"pill_class": "idle",    "prefix": "⏸"},
    "running": {"pill_class": "running", "prefix": "⚡"},
    "done":    {"pill_class": "done",    "prefix": "✅"},
    "error":   {"pill_class": "error",   "prefix": "✗"},
}


# ──────────────────────────────────────────────────────────────────────────────
# Public renderer
# ──────────────────────────────────────────────────────────────────────────────

def render_agent_panel(collapsed: bool = False) -> None:
    """
    Render the agent-progress panel.

    Parameters
    ----------
    collapsed : if True, wrap inside a Streamlit expander so it can be hidden.
    """
    statuses: list[dict] = st.session_state.get("agent_statuses", [])

    if collapsed:
        with st.expander("🤖  Agent Progress", expanded=True):
            _render_panel_body(statuses)
    else:
        _render_panel_body(statuses)


def render_agent_panel_compact() -> None:
    """
    A slim one-line badge strip showing all agents at a glance.
    Useful for embedding in the chat header area.
    """
    statuses: list[dict] = st.session_state.get("agent_statuses", [])
    badges = ""
    for agent in statuses:
        cfg     = _STATUS_CONFIG.get(agent["status"], _STATUS_CONFIG["idle"])
        pill_cls = cfg["pill_class"]
        prefix   = cfg["prefix"]
        badges += (
            f'<span class="status-pill {pill_cls}" style="margin-right:6px;">'
            f'{agent["icon"]} {agent["name"]} {prefix}</span>'
        )

    st.markdown(
        f'<div style="padding:4px 0 8px;">{badges}</div>',
        unsafe_allow_html=True,
    )


# ──────────────────────────────────────────────────────────────────────────────
# Private helpers
# ──────────────────────────────────────────────────────────────────────────────

def _render_panel_body(statuses: list[dict]) -> None:
    """Render the full panel HTML."""
    rows_html = _build_rows_html(statuses)
    overall   = _compute_overall_status(statuses)
    progress  = _compute_progress(statuses)

    st.markdown(
        f"""
        <div class="agent-panel">
            <div style="display:flex;align-items:center;justify-content:space-between;
                        margin-bottom:10px;">
                <span class="agent-panel-title">🤖 Agent Pipeline</span>
                <span class="status-pill {_STATUS_CONFIG.get(overall, _STATUS_CONFIG['idle'])['pill_class']}">
                    {overall.upper()}
                </span>
            </div>
            {rows_html}
            {_progress_bar_html(progress)}
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Reset button (only shown when all done or any error)
    if overall in ("done", "error"):
        if st.button("↺  Reset Agents", key="btn_reset_agents"):
            reset_agent_statuses()
            st.rerun()


def _build_rows_html(statuses: list[dict]) -> str:
    """Build one <div class="agent-step"> per agent."""
    html_parts: list[str] = []

    for agent in statuses:
        status  = agent.get("status", "idle")
        cfg     = _STATUS_CONFIG.get(status, _STATUS_CONFIG["idle"])
        pill_cls = cfg["pill_class"]
        prefix   = cfg["prefix"]
        detail   = agent.get("detail", "")

        # Running agents get a pulsing dot animation
        pulse_html = '<span class="pulse"></span>' if status == "running" else ""

        html_parts.append(
            f"""
            <div class="agent-step">
                <span class="agent-icon">{agent.get("icon", "🤖")}</span>
                <span class="agent-name">{agent.get("name", "Agent")}</span>
                {pulse_html}
                <span class="agent-status" style="margin-left:auto;">
                    <span class="status-pill {pill_cls}">
                        {prefix} {detail}
                    </span>
                </span>
            </div>
            """
        )

    return "".join(html_parts)


def _compute_overall_status(statuses: list[dict]) -> str:
    """
    Derive a single overall status from the agent list.
    - Any error   → "error"
    - Any running → "running"
    - All done    → "done"
    - Otherwise   → "idle"
    """
    status_set = {a["status"] for a in statuses}
    if "error"   in status_set:
        return "error"
    if "running" in status_set:
        return "running"
    if status_set == {"done"}:
        return "done"
    return "idle"


def _compute_progress(statuses: list[dict]) -> float:
    """Return a 0.0–1.0 progress fraction based on done/total agents."""
    if not statuses:
        return 0.0
    done = sum(1 for a in statuses if a["status"] == "done")
    return done / len(statuses)


def _progress_bar_html(fraction: float) -> str:
    """Render a thin CSS progress bar (0–100%)."""
    pct = int(fraction * 100)
    return f"""
    <div style="margin-top:10px;background:var(--border-color);
                border-radius:4px;height:4px;overflow:hidden;">
        <div style="width:{pct}%;height:100%;
                    background:var(--accent);
                    border-radius:4px;
                    transition:width 0.5s ease;">
        </div>
    </div>
    <div style="font-size:0.72rem;color:var(--text-secondary);
                text-align:right;margin-top:4px;">{pct}% complete</div>
    """
