"""Returns the configured embedding provider — the only place EMBEDDING_PROVIDER is read."""

from functools import lru_cache

from app.config.settings import settings
from app.core.exceptions import EmbeddingError
from app.embeddings.base import BaseEmbeddingProvider
from app.embeddings.huggingface_embeddings import HuggingFaceEmbeddingProvider
from app.embeddings.openai_embeddings import OpenAIEmbeddingProvider


@lru_cache
def get_embedding_provider() -> BaseEmbeddingProvider:
    if settings.EMBEDDING_PROVIDER == "openai":
        return OpenAIEmbeddingProvider()
    if settings.EMBEDDING_PROVIDER == "huggingface":
        return HuggingFaceEmbeddingProvider()
    if settings.EMBEDDING_PROVIDER == "gemini":
        from app.embeddings.gemini_embeddings import GeminiEmbeddingProvider
        return GeminiEmbeddingProvider()
    raise EmbeddingError(f"Unknown EMBEDDING_PROVIDER '{settings.EMBEDDING_PROVIDER}'.")
