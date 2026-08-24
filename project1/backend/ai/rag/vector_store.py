"""
ai/rag/vector_store.py — Vector Store Abstraction
===================================================
Unified interface for ChromaDB (dev) and pgvector (production).
Selected by VECTOR_STORE_TYPE in settings.
"""

from __future__ import annotations
import os
from backend.core.config import settings
from backend.core.logging import get_logger

logger = get_logger(__name__)


def get_vector_store(collection_name: str):
    """
    Return a LangChain VectorStore for the given collection.
    ChromaDB is used locally; pgvector in production.
    """
    if settings.VECTOR_STORE_TYPE == "pgvector":
        return _get_pgvector_store(collection_name)
    return _get_chroma_store(collection_name)


def _get_chroma_store(collection_name: str):
    from langchain_community.vectorstores import Chroma
    from backend.ai.llm import get_embeddings
    os.makedirs(settings.CHROMA_PERSIST_DIR, exist_ok=True)
    return Chroma(
        collection_name=collection_name,
        embedding_function=get_embeddings(),
        persist_directory=settings.CHROMA_PERSIST_DIR,
    )


def _get_pgvector_store(collection_name: str):
    from langchain_community.vectorstores import PGVector
    from backend.ai.llm import get_embeddings
    return PGVector(
        collection_name=collection_name,
        embedding_function=get_embeddings(),
        connection_string=settings.database_url_sync,
    )


def get_user_collection_name(user_id) -> str:
    """Each user gets an isolated collection to prevent cross-user retrieval."""
    return f"user_{str(user_id).replace('-', '')}"
