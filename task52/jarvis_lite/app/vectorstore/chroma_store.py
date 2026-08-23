"""ChromaDB-backed vector store — the primary backend.

Persists locally under `settings.VECTOR_DB_PATH` via Chroma's
`PersistentClient`, so embeddings survive process restarts with no
extra work on our part.
"""

import logging
from typing import List

from app.chunking.chunker import DocumentChunk
from app.config.settings import settings
from app.core.exceptions import VectorStoreError
from app.vectorstore.base import BaseVectorStore, VectorSearchResult

logger = logging.getLogger(__name__)


class ChromaVectorStore(BaseVectorStore):
    def __init__(self, collection_name: str = None) -> None:
        try:
            import chromadb
        except ImportError as exc:
            raise VectorStoreError(
                "chromadb is not installed. Run `pip install -r requirements.txt`."
            ) from exc

        settings.vector_db_path.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=str(settings.vector_db_path))
        self._collection_name = collection_name or settings.COLLECTION_NAME
        self._collection = None
        self.create_collection(self._collection_name)

    def create_collection(self, name: str) -> None:
        try:
            self._collection = self._client.get_or_create_collection(
                name=name, metadata={"hnsw:space": "cosine"}
            )
            self._collection_name = name
        except Exception as exc:
            logger.exception("Failed to create/open Chroma collection %s", name)
            raise VectorStoreError(f"Could not create collection '{name}': {exc}") from exc

    def add_chunks(self, chunks: List[DocumentChunk], embeddings: List[List[float]]) -> None:
        if len(chunks) != len(embeddings):
            raise VectorStoreError(
                f"Chunk/embedding count mismatch: {len(chunks)} chunks vs {len(embeddings)} embeddings."
            )
        if not chunks:
            return

        try:
            self._collection.upsert(
                ids=[c.chunk_id for c in chunks],
                embeddings=embeddings,
                documents=[c.content for c in chunks],
                metadatas=[c.metadata for c in chunks],
            )
        except Exception as exc:
            logger.exception("Failed to add %d chunk(s) to Chroma", len(chunks))
            raise VectorStoreError(f"Failed to store chunks in Chroma: {exc}") from exc

        logger.info("Added %d chunk(s) to Chroma collection '%s'", len(chunks), self._collection_name)

    def similarity_search(self, query_embedding: List[float], top_k: int) -> List[VectorSearchResult]:
        try:
            count = self._collection.count()
        except Exception as exc:
            raise VectorStoreError(f"Could not read collection size: {exc}") from exc

        if count == 0:
            return []

        try:
            results = self._collection.query(
                query_embeddings=[query_embedding],
                n_results=min(top_k, count),
                include=["documents", "metadatas", "distances"],
            )
        except Exception as exc:
            logger.exception("Chroma similarity search failed")
            raise VectorStoreError(f"Similarity search failed: {exc}") from exc

        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        # Cosine distance -> similarity in [0, 1] (approx.; distance can exceed 1 in edge cases).
        return [
            VectorSearchResult(content=doc, metadata=meta or {}, score=max(0.0, 1.0 - dist))
            for doc, meta, dist in zip(documents, metadatas, distances)
        ]

    def delete_collection(self, name: str) -> None:
        try:
            self._client.delete_collection(name)
        except Exception as exc:
            logger.exception("Failed to delete Chroma collection %s", name)
            raise VectorStoreError(f"Could not delete collection '{name}': {exc}") from exc

    def persist(self) -> None:
        # PersistentClient writes through on every call — nothing to flush explicitly.
        pass
