"""
BM25 keyword retrieval service — Phase 10.

Uses rank-bm25 (pure-Python BM25Okapi) to score chunks against a
keyword query.  Because BM25 is an in-memory index we build it on the
fly from all chunks belonging to a user.  For most workloads (< 50k
chunks per user) this is fast enough; a persistent index (Elasticsearch,
Redis Search) can replace this later without changing the interface.

The function returns the same RetrievedChunk dataclass as vector
retrieval, tagged with retrieval_method="bm25", so hybrid_retrieval can
merge the two result sets uniformly.
"""

import logging
import re
import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.chunk import DocumentChunk
from app.models.document import Document
from app.services.vector_retrieval import RetrievedChunk

logger = logging.getLogger(__name__)

_DEFAULT_TOP_K = 6

# ---------------------------------------------------------------------------
# Simple tokeniser (no external NLP dependency)
# ---------------------------------------------------------------------------
_TOKEN_RE = re.compile(r"[a-z0-9]+")

_STOPWORDS = frozenset(
    "a an the and or but in on at to for of is are was were be been "
    "being have has had do does did will would could should may might "
    "it its this that these those with from by as if not no".split()
)


def _tokenise(text: str) -> List[str]:
    tokens = _TOKEN_RE.findall(text.lower())
    return [t for t in tokens if t not in _STOPWORDS and len(t) > 1]


# ---------------------------------------------------------------------------
# BM25 search
# ---------------------------------------------------------------------------


def bm25_search(
    db: Session,
    user_id: uuid.UUID,
    query: str,
    top_k: int = _DEFAULT_TOP_K,
    document_ids: Optional[List[uuid.UUID]] = None,
) -> List[RetrievedChunk]:
    """
    Perform BM25 keyword retrieval over all chunks for the given user.
    Returns up to `top_k` results, sorted by descending BM25 score.
    """
    try:
        from rank_bm25 import BM25Okapi  # lazy import — optional dep
    except ImportError as exc:
        logger.error("rank-bm25 not installed: %s", exc)
        return []

    # ── 1. Fetch all eligible chunks from DB ────────────────────────────────
    stmt = (
        select(DocumentChunk, Document.filename.label("document_name"))
        .join(Document, DocumentChunk.document_id == Document.id)
        .where(DocumentChunk.user_id == user_id)
    )
    if document_ids:
        stmt = stmt.where(DocumentChunk.document_id.in_(document_ids))

    rows = db.execute(stmt).all()
    if not rows:
        return []

    chunks: List[DocumentChunk] = [r[0] for r in rows]
    doc_names: List[str] = [r[1] for r in rows]

    # ── 2. Build BM25 index ──────────────────────────────────────────────────
    tokenised_corpus = [_tokenise(c.content) for c in chunks]
    bm25 = BM25Okapi(tokenised_corpus)

    # ── 3. Score and rank ────────────────────────────────────────────────────
    query_tokens = _tokenise(query)
    if not query_tokens:
        return []

    scores = bm25.get_scores(query_tokens)

    # Pair each chunk with its score and sort descending
    ranked = sorted(
        zip(scores, chunks, doc_names), key=lambda x: x[0], reverse=True
    )[:top_k]

    results: List[RetrievedChunk] = []
    max_score = ranked[0][0] if ranked else 1.0  # for normalisation

    for raw_score, chunk, doc_name in ranked:
        if raw_score <= 0:
            continue
        # Normalise BM25 score to [0, 1] so it's comparable to cosine sim
        normalised = raw_score / max_score if max_score > 0 else 0.0
        results.append(
            RetrievedChunk(
                chunk_id=chunk.id,
                document_id=chunk.document_id,
                document_name=doc_name,
                content=chunk.content,
                chunk_index=chunk.chunk_index,
                page_number=chunk.page_number,
                score=normalised,
                retrieval_method="bm25",
            )
        )

    logger.debug(
        "bm25_search: query=%r user=%s top_k=%d → %d results",
        query[:60],
        user_id,
        top_k,
        len(results),
    )
    return results
