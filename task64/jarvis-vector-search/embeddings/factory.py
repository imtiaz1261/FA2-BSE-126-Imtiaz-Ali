"""
embeddings/factory.py
-----------------------
Builds the configured embedding provider so the rest of the app
depends only on the BaseEmbeddingProvider interface.
"""
from config import Config
from embeddings.base import BaseEmbeddingProvider
from exceptions import ConfigurationError
from logger import get_logger

logger = get_logger(__name__)


def get_embedding_provider(config: Config) -> BaseEmbeddingProvider:
    provider = config.embedding_provider

    if provider == "sentence_transformers":
        from embeddings.sentence_transformer_provider import SentenceTransformerEmbeddingProvider
        return SentenceTransformerEmbeddingProvider(
            model_name=config.embedding_model, batch_size=config.batch_size
        )

    if provider == "openai":
        from embeddings.openai_provider import OpenAIEmbeddingProvider
        model = config.embedding_model
        if model == "all-MiniLM-L6-v2":  # default was written for ST; swap to a sane OpenAI default
            model = "text-embedding-3-small"
        return OpenAIEmbeddingProvider(model_name=model, api_key=config.openai_api_key)

    if provider == "local_tfidf":
        from embeddings.local_tfidf_provider import LocalTfidfEmbeddingProvider
        logger.warning(
            "Using local_tfidf embedding provider — offline fallback for dev/testing, "
            "not recommended for production semantic quality."
        )
        return LocalTfidfEmbeddingProvider()

    raise ConfigurationError(f"Unknown embedding provider: {provider}")
