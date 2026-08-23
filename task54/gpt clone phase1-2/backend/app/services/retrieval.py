"""
Hybrid retrieval service combining BM25 keyword search with vector similarity.

Implements:
- BM25 (Okapi) full-text search for keyword matching
- Vector similarity search using pgvector
- Result merging and reranking
- Citation extraction
"""

import logging
import uuid
from typing import Optional

from sqlalchemy import and_, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    DocumentChunk,
    DocumentEmbedding,
    UploadedDocument,
)
from app.services.embeddings import get_embedding_service

logger = logging.getLogger(__name__)

# ============================================================================
# Configuration
# ============================================================================

DEFAULT_TOP_K = 5  # Top K chunks to retrieve
BM25_WEIGHT = 0.3  # Weight for BM25 score in hybrid search
VECTOR_WEIGHT = 0.7  # Weight for vector similarity in hybrid search


# ============================================================================
# BM25 Search
# ============================================================================


async def bm25_search(
    session: AsyncSession,
    query: str,
    conversation_id: Optional[uuid.UUID] = None,
    user_id: Optional[uuid.UUID] = None,
    top_k: int = DEFAULT_TOP_K,
) -> list[tuple[uuid.UUID, float]]:
    """
    BM25 keyword search on document chunks.

    Uses PostgreSQL full-text search with BM25 ranking.

    Args:
        session: Database session
        query: Search query
        conversation_id: Optional conversation scope
        user_id: Optional user scope
        top_k: Number of results to return

    Returns:
        List of (chunk_id, bm25_score) tuples, highest score first
    """
    if not query or not query.strip():
        return []

    try:
        # Build SQL query with BM25 scoring
        base_query = select(
            DocumentChunk.id,
            func.ts_rank(
                func.to_tsvector("english", DocumentChunk.text),
                func.websearch_to_tsquery("english", query),
                32,  # RANK_BM25
            ).label("bm25_score"),
        ).join(
            UploadedDocument, DocumentChunk.document_id == UploadedDocument.id
        )

        # Filter by conversation if provided
        if conversation_id:
            base_query = base_query.where(
                UploadedDocument.conversation_id == conversation_id
            )

        # Filter by user if provided
        if user_id:
            base_query = base_query.where(UploadedDocument.user_id == user_id)

        # Filter by ready status
        base_query = base_query.where(UploadedDocument.status == "ready")

        # Full-text search
        base_query = base_query.where(
            func.to_tsvector("english", DocumentChunk.text).op("@@")(
                func.websearch_to_tsquery("english", query)
            )
        )

        # Sort by score descending and limit
        base_query = base_query.order_by(text("bm25_score DESC")).limit(top_k)

        result = await session.execute(base_query)
        rows = result.all()

        results = [(row[0], float(row[1])) for row in rows]
        logger.debug(f"BM25 search found {len(results)} results for query: {query}")

        return results

    except Exception as e:
        logger.error(f"BM25 search error: {e}")
        return []


# ============================================================================
# Vector Similarity Search
# ============================================================================


async def vector_search(
    session: AsyncSession,
    query_embedding: list[float],
    conversation_id: Optional[uuid.UUID] = None,
    user_id: Optional[uuid.UUID] = None,
    top_k: int = DEFAULT_TOP_K,
) -> list[tuple[uuid.UUID, float]]:
    """
    Vector similarity search on embeddings.

    Uses pgvector cosine similarity distance.

    Args:
        session: Database session
        query_embedding: Query embedding vector
        conversation_id: Optional conversation scope
        user_id: Optional user scope
        top_k: Number of results to return

    Returns:
        List of (chunk_id, similarity_score) tuples, highest score first
    """
    try:
        # Build query with cosine distance
        base_query = select(
            DocumentEmbedding.chunk_id,
            (1 - (DocumentEmbedding.embedding.op("<->>")(query_embedding))).label(
                "similarity"
            ),
        ).join(
            UploadedDocument,
            DocumentEmbedding.document_id == UploadedDocument.id,
        )

        # Filter by conversation if provided
        if conversation_id:
            base_query = base_query.where(
                UploadedDocument.conversation_id == conversation_id
            )

        # Filter by user if provided
        if user_id:
            base_query = base_query.where(UploadedDocument.user_id == user_id)

        # Filter by ready status
        base_query = base_query.where(UploadedDocument.status == "ready")

        # Sort by similarity descending and limit
        base_query = base_query.order_by(
            text("similarity DESC")
        ).limit(top_k * 2)  # Get more candidates for merging

        result = await session.execute(base_query)
        rows = result.all()

        results = [(row[0], float(row[1])) for row in rows]
        logger.debug(f"Vector search found {len(results)} results")

        return results

    except Exception as e:
        logger.error(f"Vector search error: {e}")
        return []


# ============================================================================
# Hybrid Search
# ============================================================================


async def hybrid_search(
    session: AsyncSession,
    query: str,
    conversation_id: Optional[uuid.UUID] = None,
    user_id: Optional[uuid.UUID] = None,
    top_k: int = DEFAULT_TOP_K,
) -> list[dict]:
    """
    Hybrid search combining BM25 and vector similarity.

    1. Run BM25 search for keyword matching
    2. Generate query embedding and run vector search
    3. Merge and rerank results
    4. Return top-k with metadata

    Args:
        session: Database session
        query: Search query
        conversation_id: Optional conversation scope
        user_id: Optional user scope
        top_k: Number of results to return

    Returns:
        List of retrieved chunks with metadata, sorted by relevance
    """
    if not query or not query.strip():
        return []

    try:
        logger.debug(f"Starting hybrid search for query: {query}")

        # Generate query embedding
        embedding_service = get_embedding_service()
        query_embedding = embedding_service.embed_text(query)

        # Run both searches in parallel (conceptually)
        bm25_results = await bm25_search(
            session, query, conversation_id, user_id, top_k * 2
        )
        vector_results = await vector_search(
            session, query_embedding, conversation_id, user_id, top_k * 2
        )

        # Merge results: normalize scores and combine with weights
        merged_scores = {}

        # Add BM25 scores
        for i, (chunk_id, bm25_score) in enumerate(bm25_results):
            # Normalize: higher score is better
            normalized_score = bm25_score / (1 + len(bm25_results))
            merged_scores[chunk_id] = {
                "bm25": normalized_score,
                "vector": 0.0,
                "hybrid": 0.0,
            }

        # Add vector scores
        for i, (chunk_id, vector_score) in enumerate(vector_results):
            if chunk_id not in merged_scores:
                merged_scores[chunk_id] = {
                    "bm25": 0.0,
                    "vector": 0.0,
                    "hybrid": 0.0,
                }
            merged_scores[chunk_id]["vector"] = vector_score

        # Calculate hybrid scores
        for chunk_id in merged_scores:
            scores = merged_scores[chunk_id]
            scores["hybrid"] = (
                scores["bm25"] * BM25_WEIGHT + scores["vector"] * VECTOR_WEIGHT
            )

        # Sort by hybrid score
        sorted_chunk_ids = sorted(
            merged_scores.keys(),
            key=lambda cid: merged_scores[cid]["hybrid"],
            reverse=True,
        )[:top_k]

        # Fetch chunk details
        chunks_query = select(
            DocumentChunk.id,
            DocumentChunk.text,
            DocumentChunk.chunk_index,
            DocumentChunk.page_number,
            UploadedDocument.id.label("document_id"),
            UploadedDocument.filename,
        ).join(
            UploadedDocument,
            DocumentChunk.document_id == UploadedDocument.id,
        ).where(
            DocumentChunk.id.in_(sorted_chunk_ids)
        )

        result = await session.execute(chunks_query)
        chunk_rows = result.all()

        # Build result list maintaining sort order
        results = []
        chunk_map = {row[0]: row for row in chunk_rows}

        for chunk_id in sorted_chunk_ids:
            if chunk_id in chunk_map:
                row = chunk_map[chunk_id]
                results.append(
                    {
                        "chunk_id": str(row[0]),
                        "document_id": str(row[4]),
                        "filename": row[5],
                        "page_number": row[3],
                        "chunk_index": row[2],
                        "text": row[1],
                        "bm25_score": merged_scores[chunk_id]["bm25"],
                        "vector_score": merged_scores[chunk_id]["vector"],
                        "relevance_score": merged_scores[chunk_id]["hybrid"],
                    }
                )

        logger.info(
            f"Hybrid search complete: query={query}, "
            f"results={len(results)}, bm25={len(bm25_results)}, "
            f"vector={len(vector_results)}"
        )

        return results

    except Exception as e:
        logger.error(f"Hybrid search error: {e}")
        return []


# ============================================================================
# Utility Functions
# ============================================================================


async def get_chunk_details(
    session: AsyncSession, chunk_id: uuid.UUID
) -> Optional[dict]:
    """Get full details of a chunk."""
    result = await session.execute(
        select(
            DocumentChunk.id,
            DocumentChunk.text,
            DocumentChunk.page_number,
            DocumentChunk.chunk_index,
            UploadedDocument.filename,
            UploadedDocument.id,
        )
        .join(
            UploadedDocument,
            DocumentChunk.document_id == UploadedDocument.id,
        )
        .where(DocumentChunk.id == chunk_id)
    )

    row = result.first()

    if not row:
        return None

    return {
        "chunk_id": str(row[0]),
        "text": row[1],
        "page_number": row[2],
        "chunk_index": row[3],
        "filename": row[4],
        "document_id": str(row[5]),
    }


async def count_conversation_chunks(
    session: AsyncSession,
    conversation_id: uuid.UUID,
) -> int:
    """Count total chunks indexed for a conversation."""
    result = await session.execute(
        select(func.count(DocumentChunk.id))
        .join(
            UploadedDocument,
            DocumentChunk.document_id == UploadedDocument.id,
        )
        .where(UploadedDocument.conversation_id == conversation_id)
        .where(UploadedDocument.status == "ready")
    )

    return result.scalar() or 0
