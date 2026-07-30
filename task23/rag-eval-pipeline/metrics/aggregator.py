"""
Aggregation logic: turns a list of per-question metric dicts into the
summary statistics the report needs (metric-wise averages, overall score,
per-category breakdown).

Kept independent of *how* the scores were computed (RAGAS vs heuristic
fallback) — it only operates on plain dicts of {metric_name: score}, so it
works identically regardless of which evaluator produced them.
"""

from __future__ import annotations

import pandas as pd


class MetricsAggregator:
    """Aggregates per-question evaluation scores into summary statistics."""

    def __init__(self, results_df: pd.DataFrame):
        """
        Args:
            results_df: One row per question, with columns:
                id, category, question, ground_truth, generated_answer,
                and one column per metric (faithfulness, answer_relevancy, ...).
        """
        self.df = results_df
        self._metric_columns = [
            c
            for c in results_df.columns
            if c
            not in {
                "id",
                "category",
                "question",
                "ground_truth",
                "generated_answer",
                "retrieved_context",
                "expected_context",
            }
        ]

    def metric_averages(self) -> dict[str, float]:
        """Average score per metric, across all questions."""
        return {m: round(float(self.df[m].mean()), 4) for m in self._metric_columns}

    def overall_score(self) -> float:
        """Single overall score: the mean of all metric averages."""
        averages = self.metric_averages()
        if not averages:
            return 0.0
        return round(sum(averages.values()) / len(averages), 4)

    def category_breakdown(self) -> pd.DataFrame:
        """Average score per metric, grouped by question category."""
        return self.df.groupby("category")[self._metric_columns].mean().round(4)

    def weakest_metric(self) -> tuple[str, float]:
        averages = self.metric_averages()
        weakest = min(averages, key=averages.get)
        return weakest, averages[weakest]

    def strongest_metric(self) -> tuple[str, float]:
        averages = self.metric_averages()
        strongest = max(averages, key=averages.get)
        return strongest, averages[strongest]

    def lowest_scoring_questions(self, metric: str, n: int = 3) -> pd.DataFrame:
        """The n questions that scored lowest on a given metric — useful for
        pointing to concrete failure cases in the report."""
        return self.df.nsmallest(n, metric)[["id", "category", "question", metric]]
