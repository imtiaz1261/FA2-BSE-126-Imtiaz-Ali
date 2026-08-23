"""Returns the configured vector store — the only place VECTOR_DB_PROVIDER is read."""

from functools import lru_cache

from app.config.settings import settings
from app.core.exceptions import VectorStoreError
from app.vectorstore.base import BaseVectorStore
from app.vectorstore.chroma_store import ChromaVectorStore
from app.vectorstore.faiss_store import FAISSVectorStore


@lru_cache
def get_vector_store() -> BaseVectorStore:
    if settings.VECTOR_DB_PROVIDER == "chroma":
        return ChromaVectorStore()
    if settings.VECTOR_DB_PROVIDER == "faiss":
        return FAISSVectorStore()
    raise VectorStoreError(f"Unknown VECTOR_DB_PROVIDER '{settings.VECTOR_DB_PROVIDER}'.")
