"""src/hybrid_retriever.py — Combines BM25 (sparse) and vector search
(dense) results into a single ranked list.

The core challenge: BM25 scores and vector similarity scores live on
completely different numeric scales (BM25 scores are often 0-20+,
similarity scores are 0-1), so you can't just add them together
directly — a BM25 score of 8 isn't "better" than a similarity score of
0.9 in any comparable sense. Min-max normalization rescales both sets of
scores to the same 0-1 range first, making a weighted combination
actually meaningful.
"""

from __future__ import annotations

from src.bm25_retriever import RetrievedDocument


def normalize_scores(results: list[RetrievedDocument]) -> dict[str, float]:
    """Min-max normalizes scores within one retriever's result list to
    the 0-1 range: (score - min) / (max - min).

    Returns a {doc_id: normalized_score} mapping. If all scores are
    identical (or there's only one result), everything normalizes to
    1.0 rather than dividing by zero.
    """
    if not results:
        return {}

    scores = [r.score for r in results]
    min_score, max_score = min(scores), max(scores)
    score_range = max_score - min_score

    normalized = {}
    for r in results:
        if score_range == 0:
            normalized[r.doc_id] = 1.0
        else:
            normalized[r.doc_id] = (r.score - min_score) / score_range
    return normalized


def hybrid_fuse(
    bm25_results: list[RetrievedDocument],
    vector_results: list[RetrievedDocument],
    bm25_weight: float,
    vector_weight: float,
    top_k: int,
) -> list[RetrievedDocument]:
    """Merges BM25 and vector search results into one deduplicated,
    re-scored, re-ranked list.

    A document that appears in BOTH result sets gets a combined score
    from both signals, which naturally tends to rank it higher than a
    document only one method found — this is the actual value of hybrid
    retrieval: documents both a keyword matcher AND a meaning matcher
    agree on are more likely to be genuinely relevant.
    """
    if abs((bm25_weight + vector_weight) - 1.0) > 1e-6:
        raise ValueError(
            f"bm25_weight ({bm25_weight}) + vector_weight ({vector_weight}) "
            f"must sum to 1.0"
        )

    bm25_normalized = normalize_scores(bm25_results)
    vector_normalized = normalize_scores(vector_results)

    # Build a lookup so we can recover document text regardless of which
    # retriever(s) found it.
    doc_texts: dict[str, str] = {}
    for r in bm25_results + vector_results:
        doc_texts[r.doc_id] = r.text

    all_doc_ids = set(bm25_normalized) | set(vector_normalized)

    fused_scores: list[RetrievedDocument] = []
    for doc_id in all_doc_ids:
        bm25_score = bm25_normalized.get(doc_id, 0.0)
        vector_score = vector_normalized.get(doc_id, 0.0)
        combined_score = (bm25_weight * bm25_score) + (vector_weight * vector_score)

        fused_scores.append(
            RetrievedDocument(
                doc_id=doc_id,
                text=doc_texts[doc_id],
                score=combined_score,
                source="hybrid",
            )
        )

    fused_scores.sort(key=lambda r: r.score, reverse=True)
    return fused_scores[:top_k]
