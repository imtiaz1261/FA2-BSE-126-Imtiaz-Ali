"""
Embedding service — Phase 9.

Wraps the OpenAI embeddings API (text-embedding-3-small by default)
so the rest of the app never touches the client directly.

Design notes:
  - Batches up to 512 texts per API call (OpenAI limit is 2048 inputs
    but 512 keeps latency predictable for large documents).
  - Returns embeddings in the same order as the input list.
  - Raises EmbeddingServiceError on any provider failure so callers
    can catch one exception type regardless of provider.
"""

import logging
from typing import List

from openai import APIError, AsyncOpenAI, AuthenticationError

from app.core.config import settings

logger = logging.getLogger(__name__)

_BATCH_SIZE = 512


class EmbeddingServiceError(Exception):
    """Raised for any provider-facing embedding error."""


def _get_client() -> AsyncOpenAI:
    # Use EMBEDDING_API_KEY if set, otherwise fall back to OPENAI_API_KEY.
    # Always point at EMBEDDING_BASE_URL (OpenAI) — not the LLM provider URL
    # (e.g. Groq) which doesn't serve an embeddings endpoint.
    api_key = settings.EMBEDDING_API_KEY or settings.OPENAI_API_KEY
    if not api_key:
        raise EmbeddingServiceError(
            "No embedding API key configured. "
            "Set EMBEDDING_API_KEY (or OPENAI_API_KEY) in your .env file."
        )
    return AsyncOpenAI(
        api_key=api_key,
        base_url=settings.EMBEDDING_BASE_URL,
    )


async def embed_texts(texts: List[str]) -> List[List[float]]:
    """
    Embed a list of strings and return a list of float vectors in the
    same order.  Empty strings are replaced with a single space so the
    API never receives an empty input.
    """
    if not texts:
        return []

    safe_texts = [t if t.strip() else " " for t in texts]
    client = _get_client()
    all_embeddings: List[List[float]] = []

    for i in range(0, len(safe_texts), _BATCH_SIZE):
        batch = safe_texts[i : i + _BATCH_SIZE]
        try:
            response = await client.embeddings.create(
                model=settings.EMBEDDING_MODEL,
                input=batch,
            )
        except AuthenticationError as exc:
            raise EmbeddingServiceError(
                "Embedding provider rejected the API key."
            ) from exc
        except APIError as exc:
            raise EmbeddingServiceError(
                f"Embedding provider error: {exc}"
            ) from exc
        except Exception as exc:
            logger.exception("Unexpected error during embedding")
            raise EmbeddingServiceError(
                f"Unexpected embedding error: {exc}"
            ) from exc

        # Response items are ordered by their index field
        sorted_data = sorted(response.data, key=lambda d: d.index)
        all_embeddings.extend([d.embedding for d in sorted_data])

    logger.debug(
        "Embedded %d text(s) with model %s", len(texts), settings.EMBEDDING_MODEL
    )
    return all_embeddings


async def embed_query(query: str) -> List[float]:
    """Convenience wrapper for embedding a single query string."""
    results = await embed_texts([query])
    return results[0]
