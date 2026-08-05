"""
Premium Research UI — Perplexity/ChatGPT Deep Research style.
Live progress timeline, credibility-scored source cards, report viewer.
"""
from __future__ import annotations
import streamlit as st
from api_client.client import api_client
from ui_components import source_card, section_header, progress_timeline, toast_error

_RESEARCH_CSS = """
<style>
.research-hero {
    background: linear-gradient(135deg, #0a0f1e 0%, #0d1535 60%, #111827 100%);
    border: 1px solid #1e2d47; border-radius: 20px;
    padding: 32px 36px; margin-bottom: 24px;
    position: relative; overflow: hidden;
}
.research-hero::before {
    content: '';
    position: absolute; top: -60px; right: -60px;
    width: 200px; height: 200px;
    background: radial-gradient(circle, rgba(79,142,247,0.08) 0%, transparent 70%);
    border-radius: 50%;
}
.research-title {
    color: #f0f4ff; font-size: 1.6rem; font-weight: 700; margin-bottom: 6px;
}
.research-subtitle { color: #64748b; font-size: 0.88rem; max-width: 560px; }

.research-input-wrap {
    background: #111827; border: 1px solid #1e2d47;
    border-radius: 14px; padding: 4px;
    transition: border-color 0.2s ease;
}
.research-input-wrap:focus-within {
    border-color: #4f8ef7;
    box-shadow: 0 0 0 3px rgba(79,142,247,0.1);
}

.report-container {
    background: linear-gradient(145deg, #0f1629, #0a0f1e);
    border: 1px solid #1e2d47; border-radius: 20px;
    padding: 32px 36px; margin-top: 16px;
    animation: fadeInUp 0.4s ease;
}
.report-container h1, .report-container h2, .report-container h3 {
    color: #f0f4ff !important;
}
.report-container p, .report-container li {
    color: #94a3b8 !important; line-height: 1.75 !important;
}

.sources-grid { display: grid; gap: 10px; margin-top: 16px; }

.step-timeline {
    background: #0f1629; border: 1px solid #1e2d47;
    border-radius: 14px; padding: 16px 20px;
    min-width: 220px;
}
</style>
"""

_STEPS = [
    "Understanding request",
    "Planning research",
    "Searching the web",
    "Reading sources",
    "Ranking information",
    "Summarizing sources",
    "Writing report",
    "Editing report",
    "Finalizing response",
]

_STEP_MAP = {s.lower().split()[0]: s for s in _STEPS}


def _match_step(raw: str) -> str:
    first = raw.lower().split()[0] if raw else ""
    return _STEP_MAP.get(first, raw)


def render_research() -> None:
    st.markdown(_RESEARCH_CSS, unsafe_allow_html=True)
    token = st.session_state.get("access_token", "")

    # ── Hero ──────────────────────────────────────────────────────────────────
    st.markdown(
        '<div class="research-hero">'
        '<div class="research-title">🔬 Deep Research</div>'
        '<div class="research-subtitle">'
        'Enter any topic and the AI will autonomously search multiple sources, '
        'rank them by credibility, extract key findings, and produce a '
        'structured, citation-backed research report.'
        '</div></div>',
        unsafe_allow_html=True,
    )

    # ── Query input ───────────────────────────────────────────────────────────
    col_q, col_btn, col_clr = st.columns([6, 1, 1])
    with col_q:
        query = st.text_area(
            "Research topic",
            placeholder="e.g.  Latest breakthroughs in open-source LLMs — August 2025",
            height=85,
            key="research_query",
            label_visibility="collapsed",
        )
    with col_btn:
        st.markdown('<div style="height:12px;"></div>', unsafe_allow_html=True)
        run = st.button("🚀 Research", type="primary", use_container_width=True,
                        key="run_research_btn")
    with col_clr:
        st.markdown('<div style="height:12px;"></div>', unsafe_allow_html=True)
        clr = st.button("Clear", use_container_width=True, key="clr_research_btn")

    if clr:
        for k in ("research_result", "research_sources", "research_query_done"):
            st.session_state.pop(k, None)
        st.rerun()

    if not run or not (query or "").strip():
        _show_prior_result()
        return

    # ── Live run ──────────────────────────────────────────────────────────────
    completed: list[str] = []
    sources: list[dict]  = []
    report: str          = ""

    main_col, timeline_col = st.columns([3, 1])

    with timeline_col:
        timeline_ph = st.empty()

    def _refresh_timeline(active: str = "") -> None:
        timeline_ph.markdown(
            progress_timeline(_STEPS, completed, active),
            unsafe_allow_html=True,
        )

    _refresh_timeline()

    with main_col:
        status_ph = st.empty()
        sources_ph = st.empty()

        with st.spinner(""):
            for kind, payload in api_client.stream_research(token, query.strip()):

                if kind == "step":
                    step_name = _match_step(payload.get("step", ""))
                    if step_name not in completed:
                        completed.append(step_name)
                    _refresh_timeline(active=step_name)
                    detail = payload.get("detail", "")
                    status_ph.markdown(
                        f'<div style="color:#f59e0b;font-size:0.85rem;'
                        f'padding:6px 0;animation:fadeIn 0.2s ease;">'
                        f'⟳ {step_name}… {detail}</div>',
                        unsafe_allow_html=True,
                    )

                elif kind == "sources":
                    sources = payload or []
                    with sources_ph.container():
                        st.markdown(
                            f'<div style="color:#22c55e;font-size:0.85rem;'
                            f'margin-bottom:10px;">✓ {len(sources)} sources found</div>',
                            unsafe_allow_html=True,
                        )
                        for i, src in enumerate(sources[:4], 1):
                            source_card(src, i, expanded=False)

                elif kind == "report":
                    report  = payload.get("report", "")
                    sources = payload.get("sources", sources)

                elif kind == "error":
                    toast_error(f"Research error: {payload}")
                    return

    # All steps done
    completed = list(_STEPS)
    _refresh_timeline()
    status_ph.empty()
    sources_ph.empty()

    st.session_state["research_result"]      = report
    st.session_state["research_sources"]     = sources
    st.session_state["research_query_done"]  = query.strip()

    _render_report(report, sources)


def _show_prior_result() -> None:
    if "research_result" not in st.session_state:
        return
    q = st.session_state.get("research_query_done", "")
    st.markdown(
        f'<div style="color:#4a5568;font-size:0.82rem;margin-bottom:12px;">'
        f'📋 Showing previous research for: <em>{q}</em></div>',
        unsafe_allow_html=True,
    )
    _render_report(
        st.session_state["research_result"],
        st.session_state.get("research_sources", []),
    )


def _render_report(report: str, sources: list[dict]) -> None:
    if not report:
        return

    # ── Actions bar ───────────────────────────────────────────────────────────
    ac1, ac2, ac3 = st.columns([2, 2, 6])
    ac1.download_button(
        "⬇ Markdown", data=report.encode(), file_name="research_report.md",
        mime="text/markdown", key=f"dl_md_{abs(hash(report))%99999}",
        use_container_width=True,
    )
    if ac2.button("📋 Copy text", key="copy_report_btn", use_container_width=True):
        st.session_state["report_copied"] = True

    st.divider()

    # ── Report ────────────────────────────────────────────────────────────────
    st.markdown('<div class="report-container">', unsafe_allow_html=True)
    st.markdown(report)
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Sources ───────────────────────────────────────────────────────────────
    if sources:
        st.markdown(
            '<div style="margin-top:28px;">'
            '<h3 style="color:#f0f4ff;font-weight:700;margin-bottom:14px;">'
            '🔗 Sources</h3></div>',
            unsafe_allow_html=True,
        )
        cols = st.columns(2)
        for i, src in enumerate(sources, 1):
            with cols[(i - 1) % 2]:
                source_card(src, i)
