"""
embeddings/local_tfidf_provider.py
------------------------------------
A zero-network-dependency embedding provider using TF-IDF + Truncated
SVD (LSA), built on scikit-learn only. Lower semantic quality than a
neural model, but useful for:
  - environments with no internet access (no model download)
  - fast local testing / CI
  - a dependency-light fallback for JARVIS-Lite

Not recommended as the production embedding backend for a real
knowledge assistant — prefer sentence_transformers or openai there.

Note: unlike neural embedding providers, this one has to be *fit* on
the full document corpus before it can embed anything (TF-IDF/SVD are
corpus-dependent). Call `fit(texts)` once via embed_documents(); after
that, embed_query() reuses the fitted vectorizer.
"""
from typing import List, Optional

import numpy as np

from embeddings.base import BaseEmbeddingProvider
from exceptions import EmbeddingError
from logger import get_logger

logger = get_logger(__name__)


class LocalTfidfEmbeddingProvider(BaseEmbeddingProvider):
    def __init__(self, n_components: int = 128):
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.decomposition import TruncatedSVD
        except ImportError as e:
            raise EmbeddingError("scikit-learn is required for local_tfidf provider") from e

        self.model_name = "local-tfidf-lsa"
        self.n_components = n_components
        self._TfidfVectorizer = TfidfVectorizer
        self._TruncatedSVD = TruncatedSVD
        self._vectorizer = None
        self._svd = None
        self._fitted = False
        self._dimension = n_components

    @property
    def dimension(self) -> int:
        return self._dimension

    def _fit(self, texts: List[str]) -> None:
        self._vectorizer = self._TfidfVectorizer(
            stop_words="english", ngram_range=(1, 2), min_df=1, max_df=0.9, sublinear_tf=True
        )
        tfidf = self._vectorizer.fit_transform(texts)
        max_components = min(tfidf.shape) - 1
        n_components = max(2, min(self.n_components, max_components))
        self._dimension = n_components
        self._svd = self._TruncatedSVD(n_components=n_components, random_state=42)
        self._svd.fit(tfidf)
        self._fitted = True
        logger.info(f"Fitted local TF-IDF/LSA vectorizer on {len(texts)} documents ({n_components} dims).")

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        if not self._fitted:
            self._fit(texts)
        try:
            tfidf = self._vectorizer.transform(texts)
            reduced = self._svd.transform(tfidf)
            norms = np.linalg.norm(reduced, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            normalized = reduced / norms
            return normalized.tolist()
        except Exception as e:
            raise EmbeddingError(f"Failed to embed documents with local_tfidf provider: {e}") from e

    def embed_query(self, text: str) -> List[float]:
        if not self._fitted:
            raise EmbeddingError(
                "local_tfidf provider must be fitted on the document corpus first "
                "(call embed_documents on your corpus before embed_query)"
            )
        tfidf = self._vectorizer.transform([text])
        reduced = self._svd.transform(tfidf)
        norm = np.linalg.norm(reduced)
        if norm == 0:
            norm = 1.0
        return (reduced[0] / norm).tolist()
