"""
components/info_panel.py
------------------------
Collapsible right-side information panel.

Displays workflow metadata that the backend will populate:
- Current workflow name
- Active agent
- Processing status
- Elapsed execution time
- Sources used (placeholder list)
- Token usage breakdown + cost estimate

All data is read from ``st.session_state.workflow_info`` which the
backend should update as agents progress.  This component is purely
display-only.
"""

from __future__ import annotations

import streamlit as st

from utils.formatters import estimated_cost, format_token_count
from utils.session import get_setting


# ── Row renderer ──────────────────────────────────────────────────────────────

def _info_row(label: str, value: str, accent: bool = False) -> None:
    """Render a single label:value row inside the panel."""
    color = "#10A37F" if accent else "inherit"
    st.markdown(
        f"""
        <div class="info-row">
            <span>{label}</span>
            <span class="info-value" style="color:{color};">{value}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ── Public renderer ───────────────────────────────────────────────────────────

def render_info_panel() -> None:
    """
    Render the collapsible info panel.

    Reads from ``st.session_state.workflow_info``.
    Visibility is gated by the ``show_info_panel`` setting.
    """
    if not get_setting("show_info_panel"):
        return

    info: dict = st.session_state.get(
        "workflow_info",
        {
            "active_agent":   "—",
            "status":         "Idle",
            "execution_time": 0.0,
            "sources":        [],
            "token_usage":    {"prompt": 0, "completion": 0, "total": 0},
        },
    )

    model = get_setting("model") or "gpt-4o-mini"

    with st.expander("ℹ️  Workflow Info", expanded=True):

        # ── Status section ────────────────────────────────────────────────
        st.markdown("<div class='info-panel'>", unsafe_allow_html=True)
        st.markdown("<h4>⚡ Execution</h4>", unsafe_allow_html=True)

        _info_row("Workflow",      "Multi-Agent Research")
        _info_row("Active Agent",  info.get("active_agent", "—"), accent=True)
        _info_row("Status",        info.get("status", "Idle"))

        exec_time = info.get("execution_time", 0.0)
        _info_row("Time Elapsed",  f"{exec_time:.1f}s")

        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Token usage ───────────────────────────────────────────────────
        tokens = info.get("token_usage", {"prompt": 0, "completion": 0, "total": 0})
        prompt_tok     = tokens.get("prompt", 0)
        completion_tok = tokens.get("completion", 0)
        total_tok      = tokens.get("total", 0)
        cost_str       = estimated_cost(prompt_tok, completion_tok, model)

        st.markdown("<div class='info-panel'>", unsafe_allow_html=True)
        st.markdown("<h4>🔢 Token Usage</h4>", unsafe_allow_html=True)

        _info_row("Model",       model)
        _info_row("Prompt",      format_token_count(prompt_tok))
        _info_row("Completion",  format_token_count(completion_tok))
        _info_row("Total",       format_token_count(total_tok), accent=True)
        _info_row("Est. Cost",   cost_str)

        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Sources ───────────────────────────────────────────────────────
        sources: list[str] = info.get("sources", [])

        st.markdown("<div class='info-panel'>", unsafe_allow_html=True)
        st.markdown("<h4>🔗 Sources</h4>", unsafe_allow_html=True)

        if sources:
            for i, src in enumerate(sources[:8], start=1):   # cap at 8
                # Truncate long URLs for display
                display = src if len(src) <= 50 else src[:47] + "…"
                st.markdown(
                    f"<div class='info-row'>"
                    f"<span style='opacity:0.5;'>{i}.</span>"
                    f"<a href='{src}' target='_blank' "
                    f"style='font-size:12px;text-overflow:ellipsis;"
                    f"overflow:hidden;white-space:nowrap;max-width:200px;'>"
                    f"{display}</a></div>",
                    unsafe_allow_html=True,
                )
        else:
            st.markdown(
                "<p style='font-size:12px;opacity:0.45;text-align:center;"
                "padding:0.5rem 0;'>No sources yet</p>",
                unsafe_allow_html=True,
            )

        st.markdown("</div>", unsafe_allow_html=True)

        # ── Placeholder notice ────────────────────────────────────────────
        st.caption("ℹ️ Data populates when connected to the backend.")
