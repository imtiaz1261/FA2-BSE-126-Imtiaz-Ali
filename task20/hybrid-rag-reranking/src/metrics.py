"""src/metrics.py — Standard information retrieval evaluation metrics.

Every function takes:
    retrieved_ids: the doc_ids a retriever returned, in ranked order
    relevant_ids:  the ground-truth set of doc_ids that are ACTUALLY
                   relevant to the query (from eval_queries.json)

These are the four metrics required by the project spec, each capturing
a different notion of "good retrieval":
    Precision@K — of the K documents returned, what fraction are relevant?
    Recall@K    — of all relevant documents that exist, what fraction did
                  we find in the top K?
    MRR         — how quickly (at what rank) did we find the FIRST
                  relevant document?
    NDCG@K      — like precision, but rewards relevant documents ranked
                  HIGHER more than the same document ranked lower.
"""

from __future__ import annotations

import math


def precision_at_k(retrieved_ids: list[str], relevant_ids: set[str], k: int) -> float:
    """Fraction of the top-K retrieved documents that are relevant.

    Example: if 2 of the top 3 retrieved documents are relevant,
    Precision@3 = 2/3 = 0.667.
    """
    if k == 0:
        return 0.0
    top_k = retrieved_ids[:k]
    num_relevant_in_top_k = sum(1 for doc_id in top_k if doc_id in relevant_ids)
    return num_relevant_in_top_k / k


def recall_at_k(retrieved_ids: list[str], relevant_ids: set[str], k: int) -> float:
    """Fraction of ALL relevant documents that were found within the
    top-K retrieved results.

    Example: if there are 3 relevant documents total, and 2 of them
    appear in the top-K retrieved, Recall@K = 2/3 = 0.667.
    """
    if not relevant_ids:
        return 0.0
    top_k = retrieved_ids[:k]
    num_relevant_found = sum(1 for doc_id in top_k if doc_id in relevant_ids)
    return num_relevant_found / len(relevant_ids)


def reciprocal_rank(retrieved_ids: list[str], relevant_ids: set[str]) -> float:
    """1 / (rank of the first relevant document), or 0 if none found.

    Example: if the first relevant document appears at rank 3 (i.e. the
    3rd result), reciprocal rank = 1/3 = 0.333. Rewards finding a
    relevant result EARLY, regardless of how many total relevant
    documents exist.
    """
    for rank, doc_id in enumerate(retrieved_ids, start=1):
        if doc_id in relevant_ids:
            return 1.0 / rank
    return 0.0


def ndcg_at_k(retrieved_ids: list[str], relevant_ids: set[str], k: int) -> float:
    """Normalized Discounted Cumulative Gain at K.

    Unlike precision, NDCG cares about ORDER: a relevant document at
    rank 1 contributes more than the same relevant document at rank 5,
    because DCG discounts each result's contribution by log2(rank + 1).
    "Normalized" means dividing by the IDEAL possible DCG (as if all
    relevant documents were ranked first), producing a 0-1 score
    comparable across queries with different numbers of relevant docs.

    Here relevance is treated as binary (1 if relevant, 0 if not) since
    our eval_queries.json doesn't have graded relevance scores.
    """
    top_k = retrieved_ids[:k]

    dcg = 0.0
    for rank, doc_id in enumerate(top_k, start=1):
        relevance = 1.0 if doc_id in relevant_ids else 0.0
        dcg += relevance / math.log2(rank + 1)

    # Ideal DCG: as if every position up to min(k, num_relevant) held a
    # relevant document.
    num_ideal = min(k, len(relevant_ids))
    ideal_dcg = sum(1.0 / math.log2(rank + 1) for rank in range(1, num_ideal + 1))

    if ideal_dcg == 0:
        return 0.0
    return dcg / ideal_dcg


def evaluate_single_query(
    retrieved_ids: list[str], relevant_ids: set[str], k: int
) -> dict[str, float]:
    """Computes all four metrics for a single query's results."""
    return {
        "precision_at_k": precision_at_k(retrieved_ids, relevant_ids, k),
        "recall_at_k": recall_at_k(retrieved_ids, relevant_ids, k),
        "mrr": reciprocal_rank(retrieved_ids, relevant_ids),
        "ndcg_at_k": ndcg_at_k(retrieved_ids, relevant_ids, k),
    }


def average_metrics(per_query_metrics: list[dict[str, float]]) -> dict[str, float]:
    """Averages metric dicts across multiple queries into one summary."""
    if not per_query_metrics:
        return {"precision_at_k": 0.0, "recall_at_k": 0.0, "mrr": 0.0, "ndcg_at_k": 0.0}

    keys = per_query_metrics[0].keys()
    return {
        key: sum(m[key] for m in per_query_metrics) / len(per_query_metrics)
        for key in keys
    }
