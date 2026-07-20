"""
vector_store.py
------------------
Stores document embeddings and performs efficient similarity search.

Two backends are supported behind one common interface:
    - "faiss"  (default): fast, in-memory, zero external services, great
                for a local project like this one.
    - "chroma": a full vector database with built-in persistence and
                metadata filtering, useful if you want to demonstrate
                working with a "real" vector DB.

Both backends store L2-normalized embeddings and use inner product (dot
product) for similarity, which is mathematically equivalent to cosine
similarity for normalized vectors.
"""

from __future__ import annotations

import logging
import os
from typing import Dict, List, Optional, Any

import numpy as np

logger = logging.getLogger(__name__)


class VectorStore:
    """Common interface for adding embeddings and performing top-K search."""

    def __init__(self, backend: str = "faiss", persist_dir: Optional[str] = None):
        self.backend = backend
        self.persist_dir = persist_dir
        self._dim: Optional[int] = None
        self._metadatas: List[Dict[str, Any]] = []

        if backend == "faiss":
            self._init_faiss()
        elif backend == "chroma":
            self._init_chroma(persist_dir)
        else:
            raise ValueError(f"Unsupported vector store backend: {backend}")

    # ------------------------------------------------------------------ #
    # FAISS backend
    # ------------------------------------------------------------------ #
    def _init_faiss(self):
        import faiss  # noqa: F401 - imported to fail fast if missing
        self._faiss = faiss
        self._index = None  # created lazily once we know the embedding dim

    def _faiss_add(self, embeddings: np.ndarray, metadatas: List[Dict[str, Any]]):
        if self._index is None:
            self._dim = embeddings.shape[1]
            # IndexFlatIP = exact search via inner product (= cosine sim
            # for normalized vectors). Fine for 100s-1000s of documents;
            # for millions of docs you'd swap in an IVF/HNSW index.
            self._index = self._faiss.IndexFlatIP(self._dim)
        self._index.add(embeddings.astype(np.float32))
        self._metadatas.extend(metadatas)

    def _faiss_search(self, query_embedding: np.ndarray, top_k: int):
        query_embedding = query_embedding.astype(np.float32).reshape(1, -1)
        scores, indices = self._index.search(query_embedding, top_k)
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:
                continue
            results.append({"score": float(score), "metadata": self._metadatas[idx]})
        return results

    # ------------------------------------------------------------------ #
    # ChromaDB backend
    # ------------------------------------------------------------------ #
    def _init_chroma(self, persist_dir: Optional[str]):
        import chromadb

        persist_dir = persist_dir or os.path.join(os.path.dirname(__file__), "..", "cache", "chroma")
        os.makedirs(persist_dir, exist_ok=True)
        self._chroma_client = chromadb.PersistentClient(path=persist_dir)
        self._collection = self._chroma_client.get_or_create_collection(
            name="documents", metadata={"hnsw:space": "cosine"}
        )

    def _chroma_add(self, embeddings: np.ndarray, metadatas: List[Dict[str, Any]]):
        ids = [str(m["doc_id"]) for m in metadatas]
        documents = [m.get("preview", "") for m in metadatas]
        self._collection.add(
            ids=ids,
            embeddings=embeddings.tolist(),
            metadatas=metadatas,
            documents=documents,
        )
        self._metadatas.extend(metadatas)

    def _chroma_search(self, query_embedding: np.ndarray, top_k: int, where: Optional[dict] = None):
        result = self._collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=top_k,
            where=where,
        )
        results = []
        for meta, dist in zip(result["metadatas"][0], result["distances"][0]):
            # chroma cosine space returns distance; convert to similarity
            similarity = 1 - dist
            results.append({"score": float(similarity), "metadata": meta})
        return results

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def add(self, embeddings: np.ndarray, metadatas: List[Dict[str, Any]]):
        """Add a batch of embeddings + associated metadata dicts."""
        if len(embeddings) != len(metadatas):
            raise ValueError("embeddings and metadatas must be the same length")
        if self.backend == "faiss":
            self._faiss_add(embeddings, metadatas)
        else:
            self._chroma_add(embeddings, metadatas)
        logger.info("Added %d vectors to %s vector store", len(embeddings), self.backend)

    def search(
        self,
        query_embedding: np.ndarray,
        top_k: int = 5,
        category_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Return the top_k most similar documents to `query_embedding`.

        Args:
            query_embedding: a single (D,) normalized embedding vector.
            top_k: number of results to return.
            category_filter: optional metadata filter (bonus feature) - if
                provided, only documents whose 'category' metadata field
                matches exactly will be considered.

        Returns:
            List of {"score": float, "metadata": dict}, sorted by
            descending similarity.
        """
        if self.backend == "faiss":
            # FAISS's IndexFlatIP has no native metadata filtering, so for
            # small corpora (this project: ~100 docs) we over-fetch and
            # filter in Python, which is simple and fast enough at scale.
            fetch_k = top_k if category_filter is None else min(len(self._metadatas), top_k * 10)
            results = self._faiss_search(query_embedding, fetch_k)
            if category_filter:
                results = [r for r in results if r["metadata"].get("category") == category_filter]
            return results[:top_k]
        else:
            where = {"category": category_filter} if category_filter else None
            return self._chroma_search(query_embedding, top_k, where=where)

    @property
    def size(self) -> int:
        return len(self._metadatas)
