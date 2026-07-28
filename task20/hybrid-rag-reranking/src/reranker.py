"""src/reranker.py — Reorders retrieved candidates using a Cross-Encoder
model for higher-precision relevance scoring.

BM25 and vector search (bi-encoders) both score query and document
INDEPENDENTLY, then compare their separately-computed representations —
fast, but limited, since the model never sees the query and document
together. A Cross-Encoder instead takes the (query, document) PAIR as a
single joint input and outputs one relevance score, letting it directly
model interactions between specific words in the query and specific words
in the document. This is far more accurate but much slower (must run
once per candidate document, not once for the whole corpus), which is
exactly why it's used ONLY to re-score a small shortlist of already
-retrieved candidates, not the entire document collection.
"""

from __future__ import annotations

from sentence_transformers import CrossEncoder

from src.bm25_retriever import RetrievedDocument


class Reranker:
    """Wraps a Hugging Face Cross-Encoder model for reranking a small
    set of candidate documents against a query."""

    def __init__(self, model_name: str) -> None:
        self._model_name = model_name
        self._model = CrossEncoder(model_name)

    def rerank(
        self, query: str, candidates: list[RetrievedDocument], top_k: int
    ) -> list[RetrievedDocument]:
        """Scores every candidate against the query with the
        cross-encoder, then returns the top_k reordered by that score.

        Returns an empty list immediately if there are no candidates,
        rather than calling the model on an empty batch.
        """
        if not candidates:
            return []

        pairs = [(query, candidate.text) for candidate in candidates]
        scores = self._model.predict(pairs)

        reranked = [
            RetrievedDocument(
                doc_id=candidate.doc_id,
                text=candidate.text,
                score=float(score),
                source="reranked",
            )
            for candidate, score in zip(candidates, scores)
        ]

        reranked.sort(key=lambda r: r.score, reverse=True)
        return reranked[:top_k]
