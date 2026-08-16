"""
vector_stores/chroma_store.py
--------------------------------
ChromaDB-backed vector store — the primary/default backend for this
module. Uses a PersistentClient so the index survives process
restarts (data is written to CHROMA_PERSIST_DIR).

Distance metric: cosine (set via collection metadata "hnsw:space").
Chroma returns cosine *distance*; we convert to similarity as
score = 1 - distance so results are consistently "higher = better"
across all vector store backends in this module.
"""
from typing import Any, Dict, List, Optional

from vector_stores.base import BaseVectorStore, SearchMatch
from exceptions import VectorStoreError
from logger import get_logger

logger = get_logger(__name__)

_MAX_BATCH = 500  # keep upserts comfortably under Chroma's internal batch limits


class ChromaVectorStore(BaseVectorStore):
    def __init__(self, persist_directory: str, collection_name: str):
        try:
            import chromadb
        except ImportError as e:
            raise VectorStoreError("chromadb is not installed. Run: pip install chromadb") from e

        self.collection_name = collection_name
        try:
            self._client = chromadb.PersistentClient(path=persist_directory)
            self._collection = self._client.get_or_create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"},
            )
            logger.info(
                f"Connected to ChromaDB collection '{collection_name}' at '{persist_directory}' "
                f"({self._collection.count()} vectors currently stored)."
            )
        except Exception as e:
            raise VectorStoreError(f"Failed to initialize ChromaDB collection: {e}") from e

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
            for start in range(0, len(ids), _MAX_BATCH):
                end = start + _MAX_BATCH
                self._collection.upsert(
                    ids=ids[start:end],
                    embeddings=embeddings[start:end],
                    documents=documents[start:end],
                    metadatas=metadatas[start:end],
                )
            logger.info(f"Upserted {len(ids)} vector(s) into '{self.collection_name}'.")
        except Exception as e:
            raise VectorStoreError(f"ChromaDB upsert failed: {e}") from e

    def query(
        self,
        query_embedding: List[float],
        top_k: int,
        where: Optional[Dict[str, Any]] = None,
    ) -> List[SearchMatch]:
        try:
            result = self._collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=self._build_where(where),
            )
        except Exception as e:
            raise VectorStoreError(f"ChromaDB query failed: {e}") from e

        matches: List[SearchMatch] = []
        ids = result.get("ids", [[]])[0]
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]

        for i, doc_id in enumerate(ids):
            distance = distances[i] if i < len(distances) else 1.0
            similarity = max(0.0, min(1.0, 1.0 - distance))
            matches.append(
                SearchMatch(
                    id=doc_id,
                    document=documents[i] if i < len(documents) else "",
                    metadata=metadatas[i] if i < len(metadatas) else {},
                    score=similarity,
                )
            )
        return matches

    def count(self) -> int:
        try:
            return self._collection.count()
        except Exception as e:
            raise VectorStoreError(f"ChromaDB count failed: {e}") from e

    def delete_collection(self) -> None:
        try:
            self._client.delete_collection(name=self.collection_name)
            logger.info(f"Deleted collection '{self.collection_name}'.")
        except Exception as e:
            raise VectorStoreError(f"Failed to delete collection: {e}") from e

    @staticmethod
    def _build_where(where: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not where:
            return None
        if len(where) == 1:
            key, value = next(iter(where.items()))
            return {key: {"$eq": value}}
        return {"$and": [{k: {"$eq": v}} for k, v in where.items()]}
