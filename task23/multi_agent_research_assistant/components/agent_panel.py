"""
components/agent_panel.py
--------------------------
Agent progress panel — two rendering modes:

1. LIVE mode  (called from app.py while processing)
   Uses ``st.status`` context manager so each agent's status card
   updates in real-time without a full page rerun.
   Entry point: ``run_pipeline_with_status(query)``

2. SUMMARY mode  (called after processing, or when idle)
   Shows the last-known agent statuses as a compact read-only panel.
   Entry point: ``render_agent_panel()``

Agent state values
------------------
"idle"    — grey
"running" — amber + pulse animation
"done"    — green
"error"   — red
"""

from __future__ import annotations

import time
from typing import Generator

import streamlit as st

from utils.formatters import agent_state_label
from utils.session import (
    set_agent_status,
    update_workflow_info,
    reset_agent_status,
    reset_workflow_info,
)

# ── Agent definitions ─────────────────────────────────────────────────────────

_AGENTS: list[dict] = [
    {
        "key":         "researcher",
        "label":       "Researcher Agent",
        "icon":        "🔍",
        "desc_idle":   "Web search & information gathering",
        "desc_run":    "Searching trusted sources…",
        "desc_done":   "Research complete ✓",
    },
    {
        "key":         "writer",
        "label":       "Writer Agent",
        "icon":        "✍️",
        "desc_idle":   "Drafting the response",
        "desc_run":    "Generating first draft…",
        "desc_done":   "Draft complete ✓",
    },
    {
        "key":         "editor",
        "label":       "Editor Agent",
        "icon":        "📝",
        "desc_idle":   "Reviewing & refining output",
        "desc_run":    "Reviewing and polishing…",
        "desc_done":   "Final response ready ✓",
    },
]

_STATE_COLORS: dict[str, str] = {
    "idle":    "#9CA3AF",
    "running": "#F59E0B",
    "done":    "#10B981",
    "error":   "#EF4444",
}

_STATE_BG: dict[str, str] = {
    "idle":    "transparent",
    "running": "rgba(245,158,11,0.10)",
    "done":    "rgba(16,185,129,0.10)",
    "error":   "rgba(239,68,68,0.10)",
}

_STATUS_ICONS: dict[str, str] = {
    "idle":    "⏸",
    "running": "⚙️",
    "done":    "✅",
    "error":   "❌",
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _overall_status(statuses: dict[str, str]) -> str:
    vals = list(statuses.values())
    if any(v == "error"   for v in vals): return "❌ Error"
    if all(v == "done"    for v in vals): return "✅ Complete"
    if any(v == "running" for v in vals): return "⚙️ Processing…"
    return "⏸ Idle"


def _dot_html(state: str) -> str:
    color = _STATE_COLORS.get(state, "#9CA3AF")
    pulse = "animation:pulse 1s infinite;" if state == "running" else ""
    return (
        f"<span style='display:inline-block;width:9px;height:9px;"
        f"border-radius:50%;background:{color};{pulse}flex-shrink:0;'></span>"
    )


# ── LIVE mode — called from app.py during processing ─────────────────────────

def run_pipeline_with_status(
    query: str,
    backend_fn,                    # callable(query) -> str  OR generator
) -> str:
    """
    Execute the backend pipeline while showing live ``st.status`` cards
    for each agent.

    Parameters
    ----------
    query      : str        The user's query string.
    backend_fn : callable   Function that accepts ``query`` and either:
                            - returns a final ``str`` response, or
                            - is a generator that yields partial tokens
                              (streaming mode).

    Returns
    -------
    str   The complete final response text.
    """
    reset_agent_status()
    reset_workflow_info()

    start_time = time.time()
    full_response = ""

    # ── Researcher ────────────────────────────────────────────────────────────
    with st.status("🔍 **Researcher Agent** — Searching trusted sources…",
                   expanded=True) as researcher_status:
        set_agent_status("researcher", "running")
        st.session_state.agent_log.append("🔍 Researcher: starting web search…")
        update_workflow_info(active_agent="Researcher", status="Searching…")
        st.write("Querying search engine and retrieving sources…")

        # The real backend calls happen inside backend_fn; we intercept
        # by letting it run while we hold the status open.  For the mock
        # we just do a placeholder sleep; the real graph calls Tavily here.
        time.sleep(0.05)          # yield to Streamlit renderer

        researcher_status.update(
            label="✅ **Researcher Agent** — Research complete",
            state="complete",
            expanded=False,
        )
        set_agent_status("researcher", "done")
        st.session_state.agent_log.append("✅ Researcher: search complete")
        update_workflow_info(active_agent="Researcher ✓")

    # ── Writer ────────────────────────────────────────────────────────────────
    with st.status("✍️ **Writer Agent** — Generating first draft…",
                   expanded=True) as writer_status:
        set_agent_status("writer", "running")
        st.session_state.agent_log.append("✍️ Writer: drafting response…")
        update_workflow_info(active_agent="Writer", status="Drafting…")
        st.write("Composing a well-structured response from research findings…")

        # ── Call the actual backend / mock here ───────────────────────────
        try:
            result = backend_fn(query)
            # Support both plain-string and generator responses
            if hasattr(result, "__next__") or hasattr(result, "__iter__") and not isinstance(result, str):
                for chunk in result:
                    full_response += chunk
            else:
                full_response = str(result)
        except Exception as exc:  # noqa: BLE001
            set_agent_status("writer", "error")
            set_agent_status("editor", "error")
            writer_status.update(
                label=f"❌ **Writer Agent** — Error: {exc}",
                state="error",
                expanded=True,
            )
            update_workflow_info(
                active_agent="—",
                status="Error",
                execution_time=round(time.time() - start_time, 2),
            )
            return f"⚠️ **Backend error:** {exc}\n\nPlease check your configuration."

        writer_status.update(
            label="✅ **Writer Agent** — Draft complete",
            state="complete",
            expanded=False,
        )
        set_agent_status("writer", "done")
        st.session_state.agent_log.append("✅ Writer: draft complete")

    # ── Editor ────────────────────────────────────────────────────────────────
    with st.status("📝 **Editor Agent** — Reviewing and polishing…",
                   expanded=True) as editor_status:
        set_agent_status("editor", "running")
        st.session_state.agent_log.append("📝 Editor: reviewing draft…")
        update_workflow_info(active_agent="Editor", status="Reviewing…")
        st.write("Checking accuracy, clarity, and completeness…")

        time.sleep(0.05)

        editor_status.update(
            label="✅ **Editor Agent** — Final response ready",
            state="complete",
            expanded=False,
        )
        set_agent_status("editor", "done")
        st.session_state.agent_log.append("✅ Editor: review complete")

    # ── Wrap up ───────────────────────────────────────────────────────────────
    elapsed = round(time.time() - start_time, 2)
    update_workflow_info(
        active_agent="—",
        status="Complete",
        execution_time=elapsed,
    )

    return full_response


# ── SUMMARY mode — idle / post-processing panel ───────────────────────────────

def render_agent_panel() -> None:
    """
    Render a compact read-only agent status summary.

    Reads ``st.session_state.agent_status`` and ``agent_log``.
    Shown below the chat when NOT actively processing.
    """
    statuses: dict[str, str] = st.session_state.get(
        "agent_status",
        {"researcher": "idle", "writer": "idle", "editor": "idle"},
    )
    log_lines: list[str] = st.session_state.get("agent_log", [])

    overall = _overall_status(statuses)
    done_count = sum(1 for v in statuses.values() if v == "done")
    total = len(_AGENTS)

    # Header
    st.markdown(
        f"""
        <div style="display:flex;align-items:center;justify-content:space-between;
                    margin-bottom:0.5rem;">
            <span style="font-size:12px;font-weight:700;letter-spacing:0.05em;
                         text-transform:uppercase;opacity:0.6;">
                🤖 Agent Pipeline
            </span>
            <span style="font-size:12px;font-weight:600;">{overall}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Agent rows
    for agent in _AGENTS:
        key   = agent["key"]
        state = statuses.get(key, "idle")
        bg    = _STATE_BG.get(state, "transparent")
        color = _STATE_COLORS.get(state, "#9CA3AF")

        if state == "done":
            desc = agent["desc_done"]
        elif state == "running":
            desc = agent["desc_run"]
        else:
            desc = agent["desc_idle"]

        st.markdown(
            f"""
            <div style="display:flex;align-items:center;gap:0.6rem;
                        padding:0.45rem 0.7rem;border-radius:9px;
                        background:{bg};margin-bottom:3px;
                        border:1px solid rgba(128,128,128,0.08);">
                <span style="font-size:17px;line-height:1;">{agent['icon']}</span>
                {_dot_html(state)}
                <div style="flex:1;min-width:0;">
                    <div style="font-size:13px;font-weight:600;line-height:1.2;">
                        {agent['label']}
                    </div>
                    <div style="font-size:11px;opacity:0.55;white-space:nowrap;
                                overflow:hidden;text-overflow:ellipsis;">
                        {desc}
                    </div>
                </div>
                <span style="font-size:11px;font-weight:500;color:{color};
                             white-space:nowrap;">
                    {_STATUS_ICONS.get(state, '')}
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Progress bar
    st.progress(done_count / total, text=f"{done_count}/{total} agents complete")

    # Activity log
    if log_lines:
        with st.expander("📋 Activity Log", expanded=False):
            log_html = "".join(
                f"<div style='font-size:11px;padding:1px 0;opacity:0.8;'>"
                f"<code>{line}</code></div>"
                for line in reversed(log_lines[-30:])
            )
            st.markdown(
                f"<div style='max-height:160px;overflow-y:auto;"
                f"font-family:monospace;'>{log_html}</div>",
                unsafe_allow_html=True,
            )

    if all(v == "idle" for v in statuses.values()):
        st.caption("ℹ️ Agent statuses update in real-time during processing.")
