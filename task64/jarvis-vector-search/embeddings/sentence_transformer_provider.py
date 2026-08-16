"""
embeddings/sentence_transformer_provider.py
--------------------------------------------
Local, open-source embeddings via the `sentence-transformers` library.
Default model: all-MiniLM-L6-v2 (384-dim, fast, good general quality).

Model downloads on first use (needs internet once); after that it's
cached locally and runs fully offline. Swap models by setting
EMBEDDING_MODEL, e.g. "all-mpnet-base-v2" for higher quality/slower.
"""
from typing import List

from embeddings.base import BaseEmbeddingProvider
from exceptions import EmbeddingError
from logger import get_logger

logger = get_logger(__name__)


class SentenceTransformerEmbeddingProvider(BaseEmbeddingProvider):
    def __init__(self, model_name: str = "all-MiniLM-L6-v2", batch_size: int = 32):
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as e:
            raise EmbeddingError(
                "sentence-transformers is not installed. Run: pip install sentence-transformers"
            ) from e

        self.model_name = model_name
        self.batch_size = batch_size
        try:
            logger.info(f"Loading sentence-transformers model '{model_name}'...")
            self._model = SentenceTransformer(model_name)
            logger.info("Model loaded successfully.")
        except Exception as e:
            raise EmbeddingError(f"Failed to load embedding model '{model_name}': {e}") from e

        self._dimension = self._model.get_sentence_embedding_dimension()

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        try:
            vectors = self._model.encode(
                texts,
                batch_size=self.batch_size,
                normalize_embeddings=True,
                show_progress_bar=False,
            )
            return [v.tolist() for v in vectors]
        except Exception as e:
            raise EmbeddingError(f"Failed to embed {len(texts)} document(s): {e}") from e

    def embed_query(self, text: str) -> List[float]:
        try:
            vector = self._model.encode([text], normalize_embeddings=True, show_progress_bar=False)[0]
            return vector.tolist()
        except Exception as e:
            raise EmbeddingError(f"Failed to embed query: {e}") from e
