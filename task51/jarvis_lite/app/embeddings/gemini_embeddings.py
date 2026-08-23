"""Google Gemini embedding provider — uses gemini-embedding-001 API."""

import logging
from typing import List

import google.generativeai as genai

from app.config.settings import settings
from app.core.exceptions import EmbeddingError
from app.embeddings.base import BaseEmbeddingProvider

logger = logging.getLogger(__name__)


class GeminiEmbeddingProvider(BaseEmbeddingProvider):
    """Embedding provider using Google Gemini API."""

    def __init__(self) -> None:
        if not settings.GEMINI_API_KEY:
            raise EmbeddingError(
                "GEMINI_API_KEY is not set. Cannot initialize Gemini embedding provider."
            )
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self._model = settings.GEMINI_EMBEDDING_MODEL

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed multiple documents using Gemini."""
        if not texts:
            return []

        try:
            result = genai.embed_content(
                model="models/gemini-embedding-001",
                content=texts,
                task_type="retrieval_document",
            )
            return result["embedding"]
        except Exception as exc:
            logger.exception("Failed to embed documents with Gemini")
            raise EmbeddingError(f"Gemini embedding failed: {exc}") from exc

    def embed_query(self, text: str) -> List[float]:
        """Embed a query using Gemini."""
        if not text:
            raise EmbeddingError("Query text cannot be empty")

        try:
            result = genai.embed_content(
                model=self._model,
                content=text,
                task_type="retrieval_query",
            )
            return result["embedding"]
        except Exception as exc:
            logger.exception("Failed to embed query with Gemini")
            raise EmbeddingError(f"Gemini query embedding failed: {exc}") from exc
