"""
vector_stores/memory_store.py
--------------------------------
Pure-Python/NumPy in-process vector store. No external DB dependency.

Intended for local development, unit tests, and CI where installing
ChromaDB/Pinecone isn't convenient — NOT for production (no
persistence across restarts, no ANN index, brute-force cosine search
only). Select it with VECTOR_DB_PROVIDER=memory.
"""
from typing import Any, Dict, List, Optional

import numpy as np

from vector_stores.base import BaseVectorStore, SearchMatch
from exceptions import VectorStoreError
from logger import get_logger

logger = get_logger(__name__)


class InMemoryVectorStore(BaseVectorStore):
    def __init__(self, collection_name: str = "memory"):
        self.collection_name = collection_name
        self._ids: List[str] = []
        self._vectors: Optional[np.ndarray] = None
        self._documents: List[str] = []
        self._metadatas: List[Dict[str, Any]] = []
        logger.info(f"Initialized in-memory vector store '{collection_name}' (dev/test use only).")

    def upsert(
        self,
        ids: List[str],
        embeddings: List[List[float]],
        documents: List[str],
        metadatas: List[Dict[str, Any]],
    ) -> None:
        if not (len(ids) == len(embeddings) == len(documents) == len(metadatas)):
            raise VectorStoreError("ids, embeddings, documents, and metadatas must be the same length")
        try:
            new_vectors = np.array(embeddings, dtype=np.float32)
            norms = np.linalg.norm(new_vectors, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            new_vectors = new_vectors / norms

            for i, doc_id in enumerate(ids):
                if doc_id in self._ids:
                    idx = self._ids.index(doc_id)
                    self._vectors[idx] = new_vectors[i]
                    self._documents[idx] = documents[i]
                    self._metadatas[idx] = metadatas[i]
                else:
                    self._ids.append(doc_id)
                    self._documents.append(documents[i])
                    self._metadatas.append(metadatas[i])
                    self._vectors = (
                        new_vectors[i:i + 1]
                        if self._vectors is None
                        else np.vstack([self._vectors, new_vectors[i:i + 1]])
                    )
            logger.info(f"Upserted {len(ids)} vector(s) into in-memory store (total: {len(self._ids)}).")
        except Exception as e:
            raise VectorStoreError(f"In-memory upsert failed: {e}") from e

    def query(
        self,
        query_embedding: List[float],
        top_k: int,
        where: Optional[Dict[str, Any]] = None,
    ) -> List[SearchMatch]:
        if self._vectors is None or len(self._ids) == 0:
            return []
        try:
            q = np.array(query_embedding, dtype=np.float32)
            q_norm = np.linalg.norm(q)
            if q_norm == 0:
                q_norm = 1.0
            q = q / q_norm

            sims = self._vectors @ q  # vectors are pre-normalized -> dot product = cosine similarity
            order = np.argsort(-sims)

            matches: List[SearchMatch] = []
            for idx in order:
                if len(matches) >= top_k:
                    break
                meta = self._metadatas[idx]
                if where and not all(str(meta.get(k, "")) == str(v) for k, v in where.items()):
                    continue
                matches.append(
                    SearchMatch(
                        id=self._ids[idx],
                        document=self._documents[idx],
                        metadata=meta,
                        score=float(max(0.0, min(1.0, sims[idx]))),
                    )
                )
            return matches
        except Exception as e:
            raise VectorStoreError(f"In-memory query failed: {e}") from e

    def count(self) -> int:
        return len(self._ids)

    def delete_collection(self) -> None:
        self._ids, self._vectors, self._documents, self._metadatas = [], None, [], []
        logger.info("Cleared in-memory vector store.")
