"""
Embedding generation and management.

Provides interface for generating embeddings using OpenAI text-embedding-3-small
with support for swapping in alternative models.
"""

import logging
from typing import Optional

import openai

from app.config import settings

logger = logging.getLogger(__name__)

# ============================================================================
# Configuration
# ============================================================================

DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSION = 1536  # text-embedding-3-small outputs 1536-dim vectors


# ============================================================================
# Embedding Service
# ============================================================================


class EmbeddingService:
    """Generate text embeddings using OpenAI API."""

    def __init__(self, model: str = DEFAULT_EMBEDDING_MODEL, api_key: Optional[str] = None):
        """
        Initialize embedding service.

        Args:
            model: Embedding model to use (default: text-embedding-3-small)
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
        """
        self.model = model
        self.api_key = api_key or settings.openai_api_key

        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not set")

        openai.api_key = self.api_key
        self._validate_model()

    def _validate_model(self) -> None:
        """Validate that model is configured correctly."""
        if self.model == "text-embedding-3-small":
            if self.embedding_dimension != EMBEDDING_DIMENSION:
                logger.warning(
                    f"Expected {EMBEDDING_DIMENSION}-dim embeddings, "
                    f"but model is configured for {self.embedding_dimension}"
                )

    @property
    def embedding_dimension(self) -> int:
        """Get embedding dimension for current model."""
        if "text-embedding-3" in self.model:
            return 1536  # Both 3-small and 3-large use 1536
        elif "text-embedding" in self.model:
            return 1536  # Default for other OpenAI models
        else:
            return 1536  # Safe default

    def embed_text(self, text: str) -> list[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector (list of floats)

        Raises:
            ValueError: If embedding fails
        """
        if not text or not text.strip():
            raise ValueError("Cannot embed empty text")

        try:
            response = openai.Embedding.create(
                input=text.strip(),
                model=self.model,
            )

            # Extract embedding from response
            embedding = response["data"][0]["embedding"]

            if len(embedding) != self.embedding_dimension:
                raise ValueError(
                    f"Expected {self.embedding_dimension}-dim embedding, "
                    f"got {len(embedding)}"
                )

            return embedding

        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            raise ValueError(f"Failed to generate embedding: {str(e)}")

    def embed_batch(self, texts: list[str], batch_size: int = 100) -> list[list[float]]:
        """
        Generate embeddings for multiple texts.

        Batches requests to optimize API usage.

        Args:
            texts: List of texts to embed
            batch_size: Size of each batch (OpenAI supports up to 2048)

        Returns:
            List of embedding vectors

        Raises:
            ValueError: If embedding fails
        """
        if not texts:
            return []

        # Filter out empty texts
        texts = [t.strip() for t in texts if t and t.strip()]

        if not texts:
            raise ValueError("All texts were empty")

        embeddings = []

        try:
            # Process in batches
            for i in range(0, len(texts), batch_size):
                batch = texts[i : i + batch_size]

                response = openai.Embedding.create(
                    input=batch,
                    model=self.model,
                )

                # Sort by index to maintain order (API doesn't guarantee order)
                sorted_embeddings = sorted(response["data"], key=lambda x: x["index"])
                batch_embeddings = [item["embedding"] for item in sorted_embeddings]

                embeddings.extend(batch_embeddings)

                logger.debug(
                    f"Embedded batch of {len(batch)} texts "
                    f"({i + len(batch)}/{len(texts)})"
                )

            return embeddings

        except Exception as e:
            logger.error(f"Batch embedding generation failed: {e}")
            raise ValueError(f"Failed to generate batch embeddings: {str(e)}")

    def get_config(self) -> dict:
        """Get embedding service configuration."""
        return {
            "model": self.model,
            "dimension": self.embedding_dimension,
            "max_batch_size": 2048,  # OpenAI limit
        }


# ============================================================================
# Global Embedding Service Instance
# ============================================================================

_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """Get or create global embedding service instance."""
    global _embedding_service

    if _embedding_service is None:
        _embedding_service = EmbeddingService()

    return _embedding_service


def set_embedding_service(service: EmbeddingService) -> None:
    """Set custom embedding service (useful for testing or swapping models)."""
    global _embedding_service
    _embedding_service = service


# ============================================================================
# Helper Functions
# ============================================================================


async def embed_text_async(text: str) -> list[float]:
    """
    Async wrapper for embedding a single text.

    Args:
        text: Text to embed

    Returns:
        Embedding vector
    """
    service = get_embedding_service()
    return service.embed_text(text)


async def embed_batch_async(texts: list[str], batch_size: int = 100) -> list[list[float]]:
    """
    Async wrapper for embedding multiple texts.

    Args:
        texts: Texts to embed
        batch_size: Batch size for API calls

    Returns:
        List of embedding vectors
    """
    service = get_embedding_service()
    return service.embed_batch(texts, batch_size=batch_size)


def create_mock_embedding(dimension: int = EMBEDDING_DIMENSION) -> list[float]:
    """
    Create a mock embedding for testing.

    Args:
        dimension: Dimension of mock embedding

    Returns:
        List of random floats
    """
    import random

    return [random.random() for _ in range(dimension)]
