"""OpenAI embeddings provider. Requires OPENAI_API_KEY in .env."""

import logging
from typing import List

from openai import APIError, AuthenticationError, OpenAI

from app.config.settings import settings
from app.core.exceptions import EmbeddingError
from app.embeddings.base import BaseEmbeddingProvider

logger = logging.getLogger(__name__)

_BATCH_SIZE = 100


class OpenAIEmbeddingProvider(BaseEmbeddingProvider):
    def __init__(self) -> None:
        if not settings.OPENAI_API_KEY:
            raise EmbeddingError(
                "EMBEDDING_PROVIDER=openai but OPENAI_API_KEY is not set in .env."
            )
        self._client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self._model = settings.OPENAI_EMBEDDING_MODEL

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        vectors: List[List[float]] = []
        for start in range(0, len(texts), _BATCH_SIZE):
            batch = texts[start : start + _BATCH_SIZE]
            vectors.extend(self._embed_batch(batch))
        return vectors

    def embed_query(self, text: str) -> List[float]:
        return self._embed_batch([text])[0]

    def _embed_batch(self, batch: List[str]) -> List[List[float]]:
        try:
            response = self._client.embeddings.create(model=self._model, input=batch)
        except AuthenticationError as exc:
            raise EmbeddingError("OpenAI rejected the API key. Check OPENAI_API_KEY.") from exc
        except APIError as exc:
            logger.exception("OpenAI embeddings request failed")
            raise EmbeddingError(f"OpenAI embeddings request failed: {exc}") from exc
        return [item.embedding for item in response.data]
