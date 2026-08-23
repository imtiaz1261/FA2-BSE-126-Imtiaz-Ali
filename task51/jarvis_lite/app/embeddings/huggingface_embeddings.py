"""Local HuggingFace Sentence-Transformers embeddings provider — no API key needed."""

import logging
from typing import List

from app.config.settings import settings
from app.core.exceptions import EmbeddingError
from app.embeddings.base import BaseEmbeddingProvider

logger = logging.getLogger(__name__)

_model_cache: dict = {}


def _load_model(model_name: str):
    """Lazily loads (and caches) the SentenceTransformer model.

    Deferred import: `sentence-transformers` pulls in torch, which is
    slow to import and unnecessary if the app only ever uses OpenAI.
    """
    if model_name not in _model_cache:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise EmbeddingError(
                "sentence-transformers is not installed. Run `pip install -r requirements.txt`."
            ) from exc

        logger.info("Loading HuggingFace embedding model '%s' (first use is slower)", model_name)
        try:
            _model_cache[model_name] = SentenceTransformer(model_name)
        except Exception as exc:
            logger.exception("Failed to load embedding model %s", model_name)
            raise EmbeddingError(f"Could not load embedding model '{model_name}': {exc}") from exc
    return _model_cache[model_name]


class HuggingFaceEmbeddingProvider(BaseEmbeddingProvider):
    def __init__(self) -> None:
        self._model_name = settings.HF_EMBEDDING_MODEL
        self._model = _load_model(self._model_name)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        try:
            vectors = self._model.encode(texts, show_progress_bar=False, convert_to_numpy=True)
        except Exception as exc:
            logger.exception("HuggingFace embedding batch failed")
            raise EmbeddingError(f"Embedding generation failed: {exc}") from exc
        return [vector.tolist() for vector in vectors]

    def embed_query(self, text: str) -> List[float]:
        return self.embed_documents([text])[0]
