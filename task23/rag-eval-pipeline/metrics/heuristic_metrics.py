"""
Lightweight, dependency-free approximations of the RAGAS metrics.

IMPORTANT: These are heuristic stand-ins, not RAGAS itself. RAGAS's real
metrics use an LLM judge to reason about faithfulness, relevancy, and
precision semantically. This module exists purely so the pipeline can be
run, tested, and demoed end-to-end without an API key. The production
evaluator (`evaluator/ragas_evaluator.py`) uses the real RAGAS metrics
whenever `LLM_PROVIDER=openai` is configured — always prefer that path for
any evaluation whose results you intend to act on.

Approximations implemented:
  - faithfulness      -> lexical overlap of the generated answer with the
                         retrieved context (does the answer stick to what
                         was retrieved?)
  - answer_relevancy  -> lexical overlap of the generated answer with the
                         question itself
  - context_precision -> lexical overlap of retrieved context with the
                         ground truth answer (did retrieval pull relevant
                         material?)
  - context_recall    -> fraction of expected_context terms that appear
                         somewhere in the retrieved context
  - answer_correctness -> lexical overlap of the generated answer with the
                         ground truth answer
"""

from __future__ import annotations

import re


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"\w+", text.lower()))


def _overlap_ratio(a: str, b: str) -> float:
    """Fraction of tokens in `a` that also appear in `b`. Returns 0.0 if `a` is empty."""
    tokens_a, tokens_b = _tokenize(a), _tokenize(b)
    if not tokens_a:
        return 0.0
    return len(tokens_a & tokens_b) / len(tokens_a)


def faithfulness(generated_answer: str, retrieved_context: list[str]) -> float:
    context_blob = " ".join(retrieved_context)
    if not generated_answer.strip():
        return 0.0
    if "don't have information" in generated_answer.lower() and not retrieved_context:
        # Correctly refusing to answer when there's no context is faithful behavior.
        return 1.0
    return round(_overlap_ratio(generated_answer, context_blob), 4)


def answer_relevancy(generated_answer: str, question: str) -> float:
    if not generated_answer.strip():
        return 0.0
    return round(_overlap_ratio(question, generated_answer), 4)


def context_precision(retrieved_context: list[str], ground_truth: str) -> float:
    if not retrieved_context:
        return 0.0
    context_blob = " ".join(retrieved_context)
    return round(_overlap_ratio(ground_truth, context_blob), 4)


def context_recall(retrieved_context: list[str], expected_context: list[str]) -> float:
    if not expected_context:
        # No expected context defined (e.g. out-of-context questions) -> recall is
        # trivially perfect only if nothing was expected AND nothing irrelevant matters.
        return 1.0
    expected_blob = " ".join(expected_context)
    retrieved_blob = " ".join(retrieved_context)
    return round(_overlap_ratio(expected_blob, retrieved_blob), 4)


def answer_correctness(generated_answer: str, ground_truth: str) -> float:
    if not generated_answer.strip():
        return 0.0
    return round(_overlap_ratio(ground_truth, generated_answer), 4)


def compute_all_heuristic_metrics(
    question: str,
    generated_answer: str,
    retrieved_context: list[str],
    ground_truth: str,
    expected_context: list[str],
) -> dict[str, float]:
    return {
        "faithfulness": faithfulness(generated_answer, retrieved_context),
        "answer_relevancy": answer_relevancy(generated_answer, question),
        "context_precision": context_precision(retrieved_context, ground_truth),
        "context_recall": context_recall(retrieved_context, expected_context),
        "answer_correctness": answer_correctness(generated_answer, ground_truth),
    }
