"""
embeddings.py
---------------
Defines the embedding model used to convert text into vectors.

Implements LangChain's `Embeddings` interface directly (embed_documents /
embed_query) so it plugs straight into `langchain_community.vectorstores.FAISS`.

Primary backend:
    Sentence-Transformers "all-MiniLM-L6-v2" - a small, fast, high quality
    pre-trained model producing 384-dimensional embeddings. Requires
    internet access the first time to download model weights from
    Hugging Face Hub.

Fallback backend (automatic):
    If sentence-transformers / its weights can't be loaded (e.g. no
    internet access), this module transparently falls back to a
    TF-IDF + Truncated SVD embedding built with scikit-learn only. This
    fallback must be *fit* on the document corpus once (during ingest),
    and that fitted state is persisted to disk alongside the FAISS index
    so that search.py can load the exact same vector space later.

Optional backend:
    OpenAI embeddings (text-embedding-3-small) - enabled by setting
    OPENAI_API_KEY in a .env file and passing use_openai=True.
"""

from __future__ import annotations

import logging
import os
from typing import List, Optional

import joblib
import numpy as np
from langchain_core.embeddings import Embeddings

logger = logging.getLogger("semantic-search.embeddings")

DEFAULT_MODEL_NAME = "all-MiniLM-L6-v2"
FALLBACK_STATE_FILENAME = "fallback_embedding_state.joblib"


class LocalEmbeddings(Embeddings):
    """
    A LangChain-compatible embedding wrapper with automatic offline
    fallback. Use the SAME instance (or one loaded via `from_saved_state`)
    for both ingestion and search so the vector space stays consistent.
    """

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL_NAME,
        index_dir: str = "faiss_index",
        force_fallback: bool = False,
        fallback_dim: int = 128,
    ):
        self.model_name = model_name
        self.index_dir = index_dir
        self.fallback_dim = fallback_dim
        self.backend: str = "uninitialized"

        self._st_model = None
        self._tfidf_vectorizer = None
        self._svd = None

        if not force_fallback:
            self._try_load_sentence_transformer()

        if self.backend != "sentence-transformers":
            self.backend = "tfidf-svd-fallback"
            self._maybe_load_fallback_state()
            if self._svd is None:
                logger.warning(
                    "sentence-transformers model unavailable (likely no "
                    "internet access to Hugging Face Hub). Using a local "
                    "TF-IDF + SVD fallback embedding instead. This will be "
                    "fit automatically the first time embed_documents() is "
                    "called on your corpus. For best retrieval quality, "
                    "install sentence-transformers with internet access."
                )

    # ------------------------------------------------------------------ #
    # Backend setup
    # ------------------------------------------------------------------ #
    def _try_load_sentence_transformer(self) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            logger.info("sentence-transformers package not installed.")
            return
        try:
            self._st_model = SentenceTransformer(self.model_name)
            self.backend = "sentence-transformers"
            logger.info("Loaded sentence-transformers model '%s'", self.model_name)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not load model '%s': %s", self.model_name, exc)

    def _fallback_state_path(self) -> str:
        os.makedirs(self.index_dir, exist_ok=True)
        return os.path.join(self.index_dir, FALLBACK_STATE_FILENAME)

    def _maybe_load_fallback_state(self) -> None:
        """If a previously-fit fallback vectorizer exists on disk (saved
        during ingest), load it so queries use the exact same vector
        space as the stored FAISS index."""
        path = self._fallback_state_path()
        if os.path.exists(path):
            state = joblib.load(path)
            self._tfidf_vectorizer = state["vectorizer"]
            self._svd = state["svd"]
            logger.info("Loaded persisted fallback embedding state from %s", path)

    def _save_fallback_state(self) -> None:
        path = self._fallback_state_path()
        joblib.dump({"vectorizer": self._tfidf_vectorizer, "svd": self._svd}, path)
        logger.info("Saved fallback embedding state to %s", path)

    def fit_fallback(self, texts: List[str]) -> None:
        """Fit the TF-IDF + SVD fallback on the document corpus. Must be
        called once, on all document chunks, before embedding queries."""
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.decomposition import TruncatedSVD

        self._tfidf_vectorizer = TfidfVectorizer(
            max_features=20000, stop_words="english", ngram_range=(1, 2)
        )
        tfidf_matrix = self._tfidf_vectorizer.fit_transform(texts)

        n_components = min(self.fallback_dim, tfidf_matrix.shape[1] - 1, tfidf_matrix.shape[0] - 1)
        n_components = max(n_components, 2)
        self._svd = TruncatedSVD(n_components=n_components, random_state=42)
        self._svd.fit(tfidf_matrix)
        self._save_fallback_state()
        logger.info(
            "Fit TF-IDF+SVD fallback embedding (dim=%d) on %d chunks", n_components, len(texts)
        )

    # ------------------------------------------------------------------ #
    # LangChain Embeddings interface
    # ------------------------------------------------------------------ #
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed a batch of document chunks. Called by FAISS.from_documents()."""
        if self.backend == "sentence-transformers":
            vectors = self._st_model.encode(
                texts, convert_to_numpy=True, normalize_embeddings=True, show_progress_bar=False
            )
            return vectors.astype(np.float32).tolist()

        # Fallback: fit on first call if not already fit/loaded from disk
        if self._svd is None:
            self.fit_fallback(texts)
        return self._encode_fallback(texts).tolist()

    def embed_query(self, text: str) -> List[float]:
        """Embed a single user query. Called by FAISS similarity_search()."""
        if self.backend == "sentence-transformers":
            vector = self._st_model.encode(
                [text], convert_to_numpy=True, normalize_embeddings=True, show_progress_bar=False
            )[0]
            return vector.astype(np.float32).tolist()

        if self._svd is None:
            raise RuntimeError(
                "Fallback embedding backend has not been fit yet. Run "
                "ingest.py first to build the index (this fits and "
                "persists the fallback vectorizer)."
            )
        return self._encode_fallback([text])[0].tolist()

    def _encode_fallback(self, texts: List[str]) -> np.ndarray:
        tfidf_matrix = self._tfidf_vectorizer.transform(texts)
        vectors = self._svd.transform(tfidf_matrix).astype(np.float32)
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1e-8
        return vectors / norms


def get_embedding_model(
    index_dir: str = "faiss_index",
    model_name: str = DEFAULT_MODEL_NAME,
    force_fallback: bool = False,
    use_openai: bool = False,
) -> Embeddings:
    """
    Factory function that returns a ready-to-use embedding model.

    Args:
        index_dir: folder where fallback vectorizer state is persisted
                   (must match the folder used for the FAISS index).
        model_name: sentence-transformers model name.
        force_fallback: force the offline TF-IDF+SVD backend.
        use_openai: use OpenAI embeddings instead (requires OPENAI_API_KEY
                    in environment / .env file and the `langchain-openai`
                    package installed).

    Returns:
        An object implementing LangChain's Embeddings interface.
    """
    if use_openai:
        try:
            from langchain_openai import OpenAIEmbeddings
        except ImportError as exc:
            raise ImportError(
                "OpenAI embeddings require the 'langchain-openai' package: "
                "pip install langchain-openai"
            ) from exc

        if not os.getenv("OPENAI_API_KEY"):
            raise EnvironmentError(
                "OPENAI_API_KEY not found. Set it in a .env file or your "
                "environment before using --use-openai."
            )
        logger.info("Using OpenAI embeddings (text-embedding-3-small)")
        return OpenAIEmbeddings(model="text-embedding-3-small")

    return LocalEmbeddings(
        model_name=model_name, index_dir=index_dir, force_fallback=force_fallback
    )