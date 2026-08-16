"""
embeddings/openai_provider.py
-------------------------------
Embeddings via OpenAI's API (e.g. text-embedding-3-small/large).
Needs OPENAI_API_KEY set. Uses the official `openai` SDK (v1+).
"""
from typing import List

from embeddings.base import BaseEmbeddingProvider
from exceptions import EmbeddingError
from logger import get_logger

logger = get_logger(__name__)

_DIMENSIONS = {
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
    "text-embedding-ada-002": 1536,
}


class OpenAIEmbeddingProvider(BaseEmbeddingProvider):
    def __init__(self, model_name: str = "text-embedding-3-small", api_key: str = ""):
        try:
            from openai import OpenAI
        except ImportError as e:
            raise EmbeddingError("openai package is not installed. Run: pip install openai") from e

        if not api_key:
            raise EmbeddingError("OPENAI_API_KEY is required for the openai embedding provider")

        self.model_name = model_name
        self._client = OpenAI(api_key=api_key)
        self._dimension = _DIMENSIONS.get(model_name, 1536)

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        try:
            response = self._client.embeddings.create(model=self.model_name, input=texts)
            return [item.embedding for item in response.data]
        except Exception as e:
            raise EmbeddingError(f"OpenAI embedding request failed: {e}") from e

    def embed_query(self, text: str) -> List[float]:
        return self.embed_documents([text])[0]
