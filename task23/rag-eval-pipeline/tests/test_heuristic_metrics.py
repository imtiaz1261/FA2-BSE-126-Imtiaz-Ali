"""Unit tests for metrics/heuristic_metrics.py."""

from __future__ import annotations

from metrics.heuristic_metrics import (
    answer_correctness,
    answer_relevancy,
    compute_all_heuristic_metrics,
    context_precision,
    context_recall,
    faithfulness,
)


def test_faithfulness_perfect_match():
    context = ["The uptime SLA is 99.9% for the Pro plan."]
    answer = "The uptime SLA is 99.9%."
    assert faithfulness(answer, context) > 0.8


def test_faithfulness_empty_answer():
    assert faithfulness("", ["some context"]) == 0.0


def test_faithfulness_correct_refusal_with_no_context():
    answer = "I don't have information about that in my knowledge base."
    assert faithfulness(answer, []) == 1.0


def test_answer_relevancy_reflects_question_overlap():
    question = "What is the uptime SLA for the Pro plan?"
    relevant_answer = "The uptime SLA for the Pro plan is 99.9%."
    irrelevant_answer = "Bananas are yellow."
    assert answer_relevancy(relevant_answer, question) > answer_relevancy(
        irrelevant_answer, question
    )


def test_context_precision_no_context_is_zero():
    assert context_precision([], "some ground truth") == 0.0


def test_context_recall_no_expected_context_defaults_to_one():
    assert context_recall(["anything"], []) == 1.0


def test_context_recall_partial_match():
    expected = ["storage limit is 5GB for the free tier"]
    retrieved = ["the free tier includes 5GB of storage"]
    score = context_recall(retrieved, expected)
    assert 0.0 < score <= 1.0


def test_answer_correctness_empty_answer_is_zero():
    assert answer_correctness("", "ground truth text") == 0.0


def test_compute_all_heuristic_metrics_returns_all_keys():
    scores = compute_all_heuristic_metrics(
        question="What is the storage limit?",
        generated_answer="The storage limit is 5GB.",
        retrieved_context=["The free tier includes 5GB of storage."],
        ground_truth="5GB",
        expected_context=["The free tier includes 5GB of storage."],
    )
    assert set(scores.keys()) == {
        "faithfulness",
        "answer_relevancy",
        "context_precision",
        "context_recall",
        "answer_correctness",
    }
    assert all(0.0 <= v <= 1.0 for v in scores.values())
