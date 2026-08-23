"""FAISS-backed vector store — optional, lightweight alternative to Chroma.

FAISS only stores vectors + integer ids, so chunk content and metadata
are kept in a sidecar JSON file next to the index, keyed by the same
ids. Vectors are L2-normalized on the way in so a plain inner-product
index (`IndexFlatIP`) behaves as cosine similarity.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List

from app.chunking.chunker import DocumentChunk
from app.config.settings import settings
from app.core.exceptions import VectorStoreError
from app.vectorstore.base import BaseVectorStore, VectorSearchResult

logger = logging.getLogger(__name__)


class FAISSVectorStore(BaseVectorStore):
    def __init__(self, collection_name: str = None) -> None:
        try:
            import faiss
            import numpy as np
        except ImportError as exc:
            raise VectorStoreError(
                "faiss-cpu/numpy is not installed. Run `pip install -r requirements.txt`."
            ) from exc

        self._faiss = faiss
        self._np = np
        settings.vector_db_path.mkdir(parents=True, exist_ok=True)

        self._collection_name = collection_name or settings.COLLECTION_NAME
        self._index = None
        self._records: Dict[int, dict] = {}
        self._next_id = 0
        self._dim = None
        self.create_collection(self._collection_name)

    def _index_path(self) -> Path:
        return settings.vector_db_path / f"{self._collection_name}.faiss"

    def _meta_path(self) -> Path:
        return settings.vector_db_path / f"{self._collection_name}.json"

    def create_collection(self, name: str) -> None:
        self._collection_name = name
        if self._index_path().exists() and self._meta_path().exists():
            self._load()
        else:
            self._index = None  # created lazily once we know the embedding dimension
            self._records = {}
            self._next_id = 0

    def _load(self) -> None:
        try:
            self._index = self._faiss.read_index(str(self._index_path()))
            meta = json.loads(self._meta_path().read_text(encoding="utf-8"))
            self._records = {int(k): v for k, v in meta["records"].items()}
            self._next_id = meta["next_id"]
            self._dim = self._index.d
        except Exception as exc:
            logger.exception("Failed to load FAISS collection %s", self._collection_name)
            raise VectorStoreError(f"Could not load collection '{self._collection_name}': {exc}") from exc

    def _ensure_index(self, dim: int) -> None:
        if self._index is None:
            self._dim = dim
            flat = self._faiss.IndexFlatIP(dim)
            self._index = self._faiss.IndexIDMap(flat)
        elif dim != self._dim:
            raise VectorStoreError(
                f"Embedding dimension changed ({self._dim} -> {dim}); use a fresh collection."
            )

    def _normalize(self, vectors):
        np = self._np
        arr = np.asarray(vectors, dtype="float32")
        norms = np.linalg.norm(arr, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return arr / norms

    def add_chunks(self, chunks: List[DocumentChunk], embeddings: List[List[float]]) -> None:
        if len(chunks) != len(embeddings):
            raise VectorStoreError(
                f"Chunk/embedding count mismatch: {len(chunks)} chunks vs {len(embeddings)} embeddings."
            )
        if not chunks:
            return

        self._ensure_index(len(embeddings[0]))
        vectors = self._normalize(embeddings)
        ids = self._np.arange(self._next_id, self._next_id + len(chunks), dtype="int64")

        try:
            self._index.add_with_ids(vectors, ids)
        except Exception as exc:
            logger.exception("Failed to add %d chunk(s) to FAISS", len(chunks))
            raise VectorStoreError(f"Failed to store chunks in FAISS: {exc}") from exc

        for internal_id, chunk in zip(ids.tolist(), chunks):
            self._records[internal_id] = {"content": chunk.content, "metadata": chunk.metadata}

        self._next_id += len(chunks)
        self.persist()
        logger.info("Added %d chunk(s) to FAISS collection '%s'", len(chunks), self._collection_name)

    def similarity_search(self, query_embedding: List[float], top_k: int) -> List[VectorSearchResult]:
        if self._index is None or self._index.ntotal == 0:
            return []

        query = self._normalize([query_embedding])
        try:
            scores, ids = self._index.search(query, min(top_k, self._index.ntotal))
        except Exception as exc:
            logger.exception("FAISS similarity search failed")
            raise VectorStoreError(f"Similarity search failed: {exc}") from exc

        results: List[VectorSearchResult] = []
        for score, internal_id in zip(scores[0].tolist(), ids[0].tolist()):
            if internal_id == -1:
                continue
            record = self._records.get(internal_id)
            if record is None:
                continue
            results.append(
                VectorSearchResult(content=record["content"], metadata=record["metadata"], score=float(score))
            )
        return results

    def delete_collection(self, name: str) -> None:
        index_path = settings.vector_db_path / f"{name}.faiss"
        meta_path = settings.vector_db_path / f"{name}.json"
        for path in (index_path, meta_path):
            if path.exists():
                path.unlink()
        if name == self._collection_name:
            self._index = None
            self._records = {}
            self._next_id = 0

    def persist(self) -> None:
        if self._index is None:
            return
        try:
            self._faiss.write_index(self._index, str(self._index_path()))
            self._meta_path().write_text(
                json.dumps({"next_id": self._next_id, "records": self._records}), encoding="utf-8"
            )
        except Exception as exc:
            logger.exception("Failed to persist FAISS collection %s", self._collection_name)
            raise VectorStoreError(f"Could not persist collection '{self._collection_name}': {exc}") from exc
