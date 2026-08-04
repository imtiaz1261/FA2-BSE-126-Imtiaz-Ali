import streamlit as st
import httpx
from charts import (
    cost_comparison_chart, latency_chart, token_usage_chart, cache_hit_chart
)

API_URL = "http://localhost:8000"


def render_dashboard():
    st.title("📊 Analytics Dashboard")

    try:
        summary = httpx.get(f"{API_URL}/metrics/summary", timeout=10).json()
    except Exception as e:
        st.error(f"Could not reach API: {e}")
        return

    if summary.get("total_requests", 0) == 0:
        st.info("No requests yet — chat or run a benchmark first.")
        return

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Requests", summary["total_requests"])
    c2.metric("Total Tokens", summary["total_tokens"])
    c3.metric("Total Cost", f"${summary['total_cost_usd']}")
    c4.metric("Avg Latency", f"{summary['avg_latency_ms']} ms")

    c5, c6 = st.columns(2)
    c5.metric("Cache Hit Rate", f"{summary['cache_hit_rate_pct']}%")
    c6.metric("LLM Calls", summary["total_llm_calls"])

    st.divider()
    st.subheader("Benchmark Report")

    if st.button("Run full benchmark (baseline, caching, prompt opt, combined)"):
        with st.spinner("Running benchmark — this calls the LLM repeatedly, may take a minute..."):
            report = httpx.post(f"{API_URL}/benchmark", json={
                "configurations": ["baseline", "caching", "prompt_optimization", "full"],
                "repeat_queries": 2,
            }, timeout=300).json()
            st.session_state["benchmark_report"] = report

    report = st.session_state.get("benchmark_report")
    if report:
        st.plotly_chart(cost_comparison_chart(report), use_container_width=True)
        st.plotly_chart(latency_chart(report), use_container_width=True)
        st.plotly_chart(token_usage_chart(report), use_container_width=True)
        st.plotly_chart(cache_hit_chart(report), use_container_width=True)
        st.json(report)
