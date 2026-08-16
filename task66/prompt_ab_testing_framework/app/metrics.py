from __future__ import annotations
import math
import pandas as pd
from scipy.stats import chi2_contingency

def compare_binary_metric(df: pd.DataFrame, metric: str = "task_completed") -> dict:
    work = df[df[metric].notna()].copy()
    a = work[work.variant == "A"][metric].astype(int)
    b = work[work.variant == "B"][metric].astype(int)
    if len(a) == 0 or len(b) == 0:
        return {"error": "Both variants need observations."}

    a_success, a_total = int(a.sum()), len(a)
    b_success, b_total = int(b.sum()), len(b)
    p_a, p_b = a_success/a_total, b_success/b_total
    diff = p_b - p_a

    se = math.sqrt(p_a*(1-p_a)/a_total + p_b*(1-p_b)/b_total)
    margin = 1.96 * se

    table = [[a_success, a_total-a_success],
             [b_success, b_total-b_success]]
    chi2, p_value, dof, expected = chi2_contingency(table, correction=False)

    return {
        "a_success": a_success, "a_total": a_total,
        "b_success": b_success, "b_total": b_total,
        "a_rate": p_a, "b_rate": p_b,
        "difference_b_minus_a": diff,
        "ci_low": diff-margin, "ci_high": diff+margin,
        "chi2": float(chi2), "p_value": float(p_value),
        "significant": bool(p_value < 0.05),
        "expected_counts": expected.tolist(),
    }

def summary(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for variant in ["A", "B"]:
        x = df[df.variant == variant]
        rows.append({
            "Variant": variant,
            "Interactions": len(x),
            "Thumbs Up %": round(100*x.feedback.eq("up").mean(), 2) if len(x) else 0,
            "Task Completion %": round(100*x.task_completed.mean(), 2)
                if x.task_completed.notna().any() else 0,
            "Avg Response Words": round(x.response_words.mean(), 1) if len(x) else 0,
            "Avg Quality Score": round(x.quality_score.mean(), 3)
                if x.quality_score.notna().any() else None,
        })
    return pd.DataFrame(rows)

def recommendation(result: dict) -> str:
    if "error" in result:
        return "Not enough data to determine a winner."
    if result["significant"]:
        if result["difference_b_minus_a"] > 0:
            return "Variant B is the statistically significant winner."
        if result["difference_b_minus_a"] < 0:
            return "Variant A is the statistically significant winner."
    return "No statistically significant winner. Continue the experiment."
