"""
Hybrid retrieval + cross-encoder reranking service — Phase 10.

Combines dense vector search (Phase 9) with BM25 keyword search
(Phase 10) using Reciprocal Rank Fusion (RRF), then optionally
re-ranks the merged candidate pool with a cross-encoder for maximum
relevance precision.

Architecture
------------

                ┌──────────────────┐
                │   User query     │
                └────────┬─────────┘
           ┌─────────────┴──────────────┐
           │                            │
    vector_search                  bm25_search
    (cosine sim)                 (BM25Okapi)
           │                            │
           └─────────── RRF Merge ──────┘
                             │
                     cross-encoder rerank
                     (sentence-transformers)
                             │
                     top-k RetrievedChunk list
                             │
                     context_selection (token budget)

Cross-encoder model
-------------------
Uses `cross-encoder/ms-marco-MiniLM-L-6-v2` — a 22M-param model that
runs comfortably on CPU, loads once at first call, and is accurate
enough for most RAG use cases.  The model is loaded lazily so startup
time is not affected when the RAG path is not used.
"""

import logging
import uuid
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.services.bm25_retrieval import bm25_search
from app.services.vector_retrieval import RetrievedChunk, vector_search

logger = logging.getLogger(__name__)

# RRF constant — 60 is the standard value from the original paper
_RRF_K = 60

# Limits for the candidate pool before reranking
_CANDIDATE_MULTIPLIER = 3  # fetch 3× top_k candidates from each method

# Cross-encoder model name (downloaded once from HuggingFace Hub)
_CROSS_ENCODER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"

_cross_encoder = None  # lazy singleton


def _get_cross_encoder():
    global _cross_encoder
    if _cross_encoder is None:
        try:
            from sentence_transformers import CrossEncoder  # lazy import

            logger.info("Loading cross-encoder model %s …", _CROSS_ENCODER_MODEL)
            _cross_encoder = CrossEncoder(_CROSS_ENCODER_MODEL)
            logger.info("Cross-encoder loaded.")
        except ImportError:
            logger.warning(
                "sentence-transformers not installed — skipping cross-encoder reranking."
            )
        except Exception as exc:
            logger.error("Failed to load cross-encoder: %s", exc)
    return _cross_encoder


# ---------------------------------------------------------------------------
# RRF merge
# ---------------------------------------------------------------------------


def _rrf_merge(
    vector_results: List[RetrievedChunk],
    bm25_results: List[RetrievedChunk],
) -> List[RetrievedChunk]:
    """
    Merge two ranked lists using Reciprocal Rank Fusion.
    Returns a list sorted by descending RRF score, deduplicated by chunk_id.
    """
    rrf_scores: Dict[uuid.UUID, float] = {}
    chunk_map: Dict[uuid.UUID, RetrievedChunk] = {}

    for rank, chunk in enumerate(vector_results, start=1):
        rrf_scores[chunk.chunk_id] = rrf_scores.get(chunk.chunk_id, 0) + 1 / (_RRF_K + rank)
        chunk_map[chunk.chunk_id] = chunk

    for rank, chunk in enumerate(bm25_results, start=1):
        rrf_scores[chunk.chunk_id] = rrf_scores.get(chunk.chunk_id, 0) + 1 / (_RRF_K + rank)
        if chunk.chunk_id not in chunk_map:
            chunk_map[chunk.chunk_id] = chunk

    sorted_ids = sorted(rrf_scores, key=lambda cid: rrf_scores[cid], reverse=True)

    merged: List[RetrievedChunk] = []
    for cid in sorted_ids:
        c = chunk_map[cid]
        # Store the RRF score as `score` for transparency
        merged.append(
            RetrievedChunk(
                chunk_id=c.chunk_id,
                document_id=c.document_id,
                document_name=c.document_name,
                content=c.content,
                chunk_index=c.chunk_index,
                page_number=c.page_number,
                score=rrf_scores[cid],
                retrieval_method="hybrid",
            )
        )
    return merged


# ---------------------------------------------------------------------------
# Cross-encoder rerank
# ---------------------------------------------------------------------------


def _rerank(query: str, candidates: List[RetrievedChunk]) -> List[RetrievedChunk]:
    """
    Re-score candidates using a cross-encoder.  Falls back to the
    original RRF ranking if the model is unavailable.
    """
    encoder = _get_cross_encoder()
    if encoder is None or not candidates:
        return candidates

    try:
        pairs = [[query, c.content] for c in candidates]
        ce_scores = encoder.predict(pairs)

        reranked = sorted(
            zip(ce_scores, candidates),
            key=lambda x: float(x[0]),
            reverse=True,
        )
        return [
            RetrievedChunk(
                chunk_id=c.chunk_id,
                document_id=c.document_id,
                document_name=c.document_name,
                content=c.content,
                chunk_index=c.chunk_index,
                page_number=c.page_number,
                score=float(score),
                retrieval_method="hybrid+rerank",
            )
            for score, c in reranked
        ]
    except Exception as exc:
        logger.warning("Cross-encoder reranking failed (%s) — using RRF order", exc)
        return candidates


# ---------------------------------------------------------------------------
# Context selection (token budget)
# ---------------------------------------------------------------------------

_CHARS_PER_TOKEN = 4  # rough approximation


def select_context(
    chunks: List[RetrievedChunk],
    max_tokens: int = 3000,
) -> List[RetrievedChunk]:
    """
    Greedily select chunks until the token budget is exhausted.
    This prevents prompt overflow for large document sets.
    """
    budget = max_tokens * _CHARS_PER_TOKEN
    selected: List[RetrievedChunk] = []
    used = 0
    for chunk in chunks:
        chunk_len = len(chunk.content)
        if used + chunk_len > budget:
            break
        selected.append(chunk)
        used += chunk_len
    return selected


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def hybrid_retrieve(
    db: Session,
    user_id: uuid.UUID,
    query: str,
    top_k: int = 6,
    document_ids: Optional[List[uuid.UUID]] = None,
    use_reranker: bool = True,
    context_max_tokens: int = 3000,
) -> List[RetrievedChunk]:
    """
    Full Phase 10 retrieval pipeline:
      1. Dense (vector) + sparse (BM25) retrieval in parallel.
      2. RRF merge.
      3. Cross-encoder rerank (if available).
      4. Token-budget context selection.

    Returns a list of RetrievedChunk objects sorted by relevance.
    """
    candidate_k = top_k * _CANDIDATE_MULTIPLIER

    # Dense retrieval (async)
    vector_results = await vector_search(
        db=db,
        user_id=user_id,
        query=query,
        top_k=candidate_k,
        document_ids=document_ids,
    )

    # Sparse retrieval (sync — BM25 is CPU-bound and fast)
    bm25_results = bm25_search(
        db=db,
        user_id=user_id,
        query=query,
        top_k=candidate_k,
        document_ids=document_ids,
    )

    # Merge
    merged = _rrf_merge(vector_results, bm25_results)

    # Rerank (CPU-bound — runs synchronously in the event loop; acceptable
    # for the cross-encoder size used; move to a thread pool if needed)
    if use_reranker:
        merged = _rerank(query, merged)

    # Trim to top_k after reranking
    merged = merged[:top_k]

    # Token-budget selection
    selected = select_context(merged, max_tokens=context_max_tokens)

    logger.info(
        "hybrid_retrieve: query=%r → vector=%d bm25=%d merged=%d selected=%d",
        query[:60],
        len(vector_results),
        len(bm25_results),
        len(merged),
        len(selected),
    )
    return selected
