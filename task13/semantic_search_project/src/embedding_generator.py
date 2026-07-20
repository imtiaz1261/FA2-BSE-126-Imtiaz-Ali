"""
embedding_generator.py
------------------------
Generates dense vector embeddings for documents / queries.

Primary backend:
    Sentence-Transformers (all-MiniLM-L6-v2) - a small, fast, high quality
    pre-trained model that produces 384-dimensional embeddings and is the
    recommended default for this project.

Fallback backend:
    If sentence-transformers (or its model weights) are unavailable, e.g.
    no internet access to Hugging Face Hub, the generator automatically
    falls back to a TF-IDF + Truncated SVD ("latent semantic") embedding
    built entirely with scikit-learn. This keeps the rest of the pipeline
    (vector store, semantic search, CLI) fully runnable for
    development/testing without requiring external downloads.

Bonus feature - embedding caching:
    Embeddings are expensive to (re)compute. This module hashes the
    document collection + model name and caches the resulting embedding
    matrix to disk (via joblib) so repeated runs skip regeneration unless
    the underlying documents or model change.
"""

from __future__ import annotations

import hashlib
import logging
import os
from typing import List, Optional

import numpy as np
import joblib

logger = logging.getLogger(__name__)

DEFAULT_MODEL_NAME = "all-MiniLM-L6-v2"
DEFAULT_CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "cache")


class EmbeddingGenerator:
    """
    Wraps a sentence-embedding backend and exposes a simple, uniform API:

        generator = EmbeddingGenerator(model_name="all-MiniLM-L6-v2")
        doc_embeddings = generator.encode(list_of_texts)
        query_embedding = generator.encode([query_text])

    Automatically falls back to a TF-IDF+SVD embedding if
    sentence-transformers / its model weights cannot be loaded (e.g. no
    network access). The fallback is fit once on the document corpus via
    `fit_fallback()` and reused for queries, so vector spaces stay
    consistent between documents and queries.
    """

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL_NAME,
        cache_dir: str = DEFAULT_CACHE_DIR,
        embedding_dim_fallback: int = 128,
        force_fallback: bool = False,
    ):
        self.model_name = model_name
        self.cache_dir = cache_dir
        self.embedding_dim_fallback = embedding_dim_fallback
        os.makedirs(self.cache_dir, exist_ok=True)

        self._backend = None  # "sentence-transformers" or "tfidf-svd"
        self._st_model = None
        self._tfidf_vectorizer = None
        self._svd = None

        if not force_fallback:
            self._try_load_sentence_transformer()
        if self._backend is None:
            logger.warning(
                "Falling back to a local TF-IDF + SVD embedding backend "
                "(sentence-transformers model unavailable, likely no "
                "internet access to Hugging Face Hub). Semantic search will "
                "still work, but for best quality use the real "
                "sentence-transformers backend when you have internet "
                "access: pip install sentence-transformers"
            )
            self._backend = "tfidf-svd"

    # ------------------------------------------------------------------ #
    # Backend setup
    # ------------------------------------------------------------------ #
    def _try_load_sentence_transformer(self) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            logger.info("sentence-transformers not installed.")
            return

        try:
            self._st_model = SentenceTransformer(self.model_name)
            self._backend = "sentence-transformers"
            logger.info("Loaded sentence-transformers model '%s'", self.model_name)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Could not load sentence-transformers model '%s' (%s).",
                self.model_name,
                exc,
            )

    def fit_fallback(self, corpus_texts: List[str]) -> None:
        """
        Fit the TF-IDF + SVD fallback vectorizer on the document corpus.
        Must be called once before encoding if the fallback backend is
        active. No-op if the sentence-transformers backend is active.
        """
        if self._backend != "tfidf-svd":
            return

        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.decomposition import TruncatedSVD

        self._tfidf_vectorizer = TfidfVectorizer(
            max_features=20000, stop_words="english", ngram_range=(1, 2)
        )
        tfidf_matrix = self._tfidf_vectorizer.fit_transform(corpus_texts)

        n_components = min(self.embedding_dim_fallback, tfidf_matrix.shape[1] - 1, tfidf_matrix.shape[0] - 1)
        n_components = max(n_components, 2)
        self._svd = TruncatedSVD(n_components=n_components, random_state=42)
        self._svd.fit(tfidf_matrix)
        logger.info(
            "Fitted TF-IDF+SVD fallback embedding (dim=%d) on %d documents",
            n_components,
            len(corpus_texts),
        )

    # ------------------------------------------------------------------ #
    # Encoding
    # ------------------------------------------------------------------ #
    def encode(self, texts: List[str], batch_size: int = 32, show_progress: bool = False) -> np.ndarray:
        """
        Encode a list of texts into an (N, D) numpy array of L2-normalized
        embeddings (so cosine similarity == dot product).
        """
        if self._backend == "sentence-transformers":
            embeddings = self._st_model.encode(
                texts,
                batch_size=batch_size,
                show_progress_bar=show_progress,
                convert_to_numpy=True,
                normalize_embeddings=True,
            )
            return embeddings.astype(np.float32)

        # TF-IDF + SVD fallback
        if self._tfidf_vectorizer is None or self._svd is None:
            raise RuntimeError(
                "Fallback embedding backend was not fitted. Call "
                "fit_fallback(corpus_texts) once on your document corpus "
                "before encoding."
            )
        tfidf_matrix = self._tfidf_vectorizer.transform(texts)
        embeddings = self._svd.transform(tfidf_matrix).astype(np.float32)
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms[norms == 0] = 1e-8
        return embeddings / norms

    @property
    def backend_name(self) -> str:
        return self._backend

    @property
    def embedding_dim(self) -> int:
        if self._backend == "sentence-transformers":
            return self._st_model.get_sentence_embedding_dimension()
        return self._svd.n_components if self._svd is not None else self.embedding_dim_fallback

    # ------------------------------------------------------------------ #
    # Caching (bonus feature)
    # ------------------------------------------------------------------ #
    @staticmethod
    def _corpus_fingerprint(texts: List[str], model_name: str) -> str:
        """Create a stable hash representing corpus content + model, used
        as a cache key so cached embeddings auto-invalidate when documents
        or the chosen model change."""
        hasher = hashlib.sha256()
        hasher.update(model_name.encode("utf-8"))
        for t in texts:
            hasher.update(t.encode("utf-8"))
        return hasher.hexdigest()[:16]

    def get_or_create_embeddings(
        self, texts: List[str], cache_name: str = "doc_embeddings", show_progress: bool = True
    ) -> np.ndarray:
        """
        Return embeddings for `texts`, using a disk cache when possible.

        If the fallback backend is active and hasn't been fitted yet, it
        will be fit on `texts` automatically (typical usage: call this once
        with the full document corpus).
        """
        fingerprint = self._corpus_fingerprint(texts, f"{self.model_name}:{self._backend}")
        cache_path = os.path.join(self.cache_dir, f"{cache_name}_{fingerprint}.joblib")

        if os.path.exists(cache_path):
            logger.info("Loading cached embeddings from %s", cache_path)
            cached = joblib.load(cache_path)
            # Restore fallback vectorizer/svd state if needed so future
            # query encodes stay consistent with this cached matrix.
            if self._backend == "tfidf-svd" and self._svd is None:
                self._tfidf_vectorizer = cached["vectorizer"]
                self._svd = cached["svd"]
            return cached["embeddings"]

        if self._backend == "tfidf-svd" and self._svd is None:
            self.fit_fallback(texts)

        embeddings = self.encode(texts, show_progress=show_progress)

        payload = {"embeddings": embeddings}
        if self._backend == "tfidf-svd":
            payload["vectorizer"] = self._tfidf_vectorizer
            payload["svd"] = self._svd

        joblib.dump(payload, cache_path)
        logger.info("Cached embeddings to %s", cache_path)
        return embeddings
