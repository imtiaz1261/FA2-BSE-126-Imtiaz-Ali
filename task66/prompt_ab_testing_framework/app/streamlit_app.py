from __future__ import annotations

from datetime import datetime, timezone

import streamlit as st

from app.ab_core import assign_variant, response_length
from app.config import settings
from app.database import insert_interaction, update_feedback, load_interactions
from app.llm import GroqLLM
from app.metrics import summary, compare_binary_metric, recommendation
st.set_page_config(page_title="Prompt A/B Testing", layout="wide")
st.title("Prompt A/B Testing Framework")
st.caption("Randomized prompt experiment • feedback • task completion • statistics")

if "assignment" not in st.session_state:
    st.session_state.assignment = None
if "response" not in st.session_state:
    st.session_state.response = None

tab1, tab2 = st.tabs(["Experiment", "Dashboard"])

with tab1:
    user_prompt = st.text_area("Enter a user request",
        placeholder="Explain recursion in Python with an example.", height=130)

    if st.button("Generate response", type="primary"):
        if not user_prompt.strip():
            st.warning("Enter a request first.")
        else:
            assignment = assign_variant(settings.variant_a_weight)
            try:
                response = GroqLLM().generate(assignment.system_prompt, user_prompt)
            except Exception as e:
                st.error(f"LLM error: {e}")
            else:
                st.session_state.assignment = assignment
                st.session_state.response = response
                insert_interaction(
                    assignment.interaction_id,
                    datetime.now(timezone.utc).isoformat(),
                    user_prompt, assignment.variant, response,
                    response_length(response))

    if st.session_state.response:
        a = st.session_state.assignment
        st.subheader(f"Response — Variant {a.variant}")
        st.write(st.session_state.response)
        st.write(f"Response length: **{response_length(st.session_state.response)} words**")

        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("👍 Helpful", key="up"):
                update_feedback(a.interaction_id, "up", 1)
                st.success("Saved.")
        with c2:
            if st.button("👎 Not helpful", key="down"):
                update_feedback(a.interaction_id, "down", 0)
                st.success("Saved.")
        with c3:
            if st.button("Task completed", key="complete"):
                update_feedback(a.interaction_id, "up", 1)
                st.success("Saved.")

with tab2:
    df = load_interactions()
    if df.empty:
        st.info("No interactions yet. Generate responses or run the demo-data script.")
    else:
        st.subheader("Variant comparison")
        st.dataframe(summary(df), use_container_width=True, hide_index=True)

        metric = st.selectbox("Primary binary metric",
            ["task_completed", "feedback"],
            format_func=lambda x: "Task completion" if x == "task_completed" else "Thumbs up")

        metric_df = df.copy()
        if metric == "feedback":
            metric_df["feedback"] = metric_df["feedback"].map({"up": 1, "down": 0})

        result = compare_binary_metric(metric_df, metric)
        if "error" not in result:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("A rate", f"{result['a_rate']:.1%}")
            c2.metric("B rate", f"{result['b_rate']:.1%}")
            c3.metric("B − A", f"{result['difference_b_minus_a']:.1%}")
            c4.metric("p-value", f"{result['p_value']:.4f}")
            st.write(f"95% CI for B − A: [{result['ci_low']:.1%}, {result['ci_high']:.1%}]")
            (st.success if result["significant"] else st.warning)(recommendation(result))
            st.bar_chart(summary(df).set_index("Variant")[["Thumbs Up %", "Task Completion %"]])

        st.subheader("Raw data")
        st.dataframe(df, use_container_width=True, hide_index=True)
