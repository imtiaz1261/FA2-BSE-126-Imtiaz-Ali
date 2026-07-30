"""Unit tests for metrics/aggregator.py."""

from __future__ import annotations

import pandas as pd
import pytest

from metrics.aggregator import MetricsAggregator


@pytest.fixture
def sample_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "id": "q01",
                "category": "fact_based",
                "question": "Q1",
                "ground_truth": "GT1",
                "generated_answer": "A1",
                "faithfulness": 1.0,
                "answer_relevancy": 0.8,
                "context_precision": 0.6,
            },
            {
                "id": "q02",
                "category": "fact_based",
                "question": "Q2",
                "ground_truth": "GT2",
                "generated_answer": "A2",
                "faithfulness": 0.5,
                "answer_relevancy": 0.4,
                "context_precision": 0.2,
            },
            {
                "id": "q03",
                "category": "edge_case",
                "question": "Q3",
                "ground_truth": "GT3",
                "generated_answer": "A3",
                "faithfulness": 0.0,
                "answer_relevancy": 0.0,
                "context_precision": 0.0,
            },
        ]
    )


def test_metric_averages(sample_df):
    agg = MetricsAggregator(sample_df)
    averages = agg.metric_averages()
    assert averages["faithfulness"] == pytest.approx(0.5)
    assert averages["answer_relevancy"] == pytest.approx(0.4)
    assert averages["context_precision"] == pytest.approx(0.2667, abs=1e-3)


def test_overall_score(sample_df):
    agg = MetricsAggregator(sample_df)
    overall = agg.overall_score()
    assert 0.0 <= overall <= 1.0


def test_weakest_and_strongest_metric(sample_df):
    agg = MetricsAggregator(sample_df)
    weakest_metric, weakest_score = agg.weakest_metric()
    strongest_metric, strongest_score = agg.strongest_metric()
    assert weakest_metric == "context_precision"
    assert strongest_metric == "faithfulness"
    assert weakest_score <= strongest_score


def test_category_breakdown(sample_df):
    agg = MetricsAggregator(sample_df)
    breakdown = agg.category_breakdown()
    assert set(breakdown.index) == {"fact_based", "edge_case"}
    assert breakdown.loc["edge_case", "faithfulness"] == 0.0


def test_lowest_scoring_questions(sample_df):
    agg = MetricsAggregator(sample_df)
    lowest = agg.lowest_scoring_questions("faithfulness", n=1)
    assert lowest.iloc[0]["id"] == "q03"


def test_empty_dataframe_metric_columns_only():
    df = pd.DataFrame(
        [{"id": "q1", "category": "fact_based", "question": "Q", "ground_truth": "G",
          "generated_answer": "A", "faithfulness": 0.9}]
    )
    agg = MetricsAggregator(df)
    assert agg.metric_averages() == {"faithfulness": 0.9}
