"""
Vector (dense) retrieval service — Phase 9.

Uses pgvector's cosine-similarity operator (<=> ) to find the top-k
document chunks closest to the query embedding.  Results are scoped to
the requesting user so no one can retrieve another user's documents.

Returned as RetrievedChunk dataclasses so downstream code (hybrid
retrieval, prompts) never touches SQLAlchemy Row objects directly.
"""

import logging
import uuid
from dataclasses import dataclass, field
from typing import List, Optional

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models.chunk import DocumentChunk
from app.models.document import Document
from app.services.embedding_service import embed_query

logger = logging.getLogger(__name__)

_DEFAULT_TOP_K = 6
_DEFAULT_SCORE_THRESHOLD = 0.0  # cosine similarity; 1.0 = identical


@dataclass
class RetrievedChunk:
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_name: str
    content: str
    chunk_index: int
    page_number: Optional[int]
    score: float  # cosine similarity (higher = more similar)
    retrieval_method: str = "vector"  # "vector" | "bm25" | "hybrid"


async def vector_search(
    db: Session,
    user_id: uuid.UUID,
    query: str,
    top_k: int = _DEFAULT_TOP_K,
    document_ids: Optional[List[uuid.UUID]] = None,
    score_threshold: float = _DEFAULT_SCORE_THRESHOLD,
) -> List[RetrievedChunk]:
    """
    Embed the query and return the top-k most similar chunks for the
    given user.  Optionally filter to a specific list of document_ids.
    """
    query_vector = await embed_query(query)

    # Build the query using pgvector's cosine-distance operator.
    # 1 - cosine_distance = cosine_similarity
    stmt = (
        select(
            DocumentChunk,
            (1 - DocumentChunk.embedding.cosine_distance(query_vector)).label("score"),
            Document.filename.label("document_name"),
        )
        .join(Document, DocumentChunk.document_id == Document.id)
        .where(
            DocumentChunk.user_id == user_id,
            DocumentChunk.embedding.is_not(None),
        )
        .order_by(DocumentChunk.embedding.cosine_distance(query_vector))
        .limit(top_k)
    )

    if document_ids:
        stmt = stmt.where(DocumentChunk.document_id.in_(document_ids))

    rows = db.execute(stmt).all()

    results: List[RetrievedChunk] = []
    for row in rows:
        chunk: DocumentChunk = row[0]
        score: float = float(row[1])
        doc_name: str = row[2]

        if score < score_threshold:
            continue

        results.append(
            RetrievedChunk(
                chunk_id=chunk.id,
                document_id=chunk.document_id,
                document_name=doc_name,
                content=chunk.content,
                chunk_index=chunk.chunk_index,
                page_number=chunk.page_number,
                score=score,
                retrieval_method="vector",
            )
        )

    logger.debug(
        "vector_search: query=%r user=%s top_k=%d → %d results",
        query[:60],
        user_id,
        top_k,
        len(results),
    )
    return results
