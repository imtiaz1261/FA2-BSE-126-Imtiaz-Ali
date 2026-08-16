"""
vector_stores/pinecone_store.py
----------------------------------
Optional Pinecone-backed vector store (managed, cloud vector DB).
Uses the pinecone-client v3+ SDK. Creates a serverless index
automatically if it doesn't exist yet.

Note: Pinecone doesn't store raw document text natively — we store it
inside each vector's metadata under the "document" key (Pinecone
metadata values must be strings/numbers/bools/lists of strings, and
there's a per-vector metadata size limit — keep chunks reasonably
sized, see config.CHUNK_SIZE).
"""
from typing import Any, Dict, List, Optional

from vector_stores.base import BaseVectorStore, SearchMatch
from exceptions import VectorStoreError
from logger import get_logger

logger = get_logger(__name__)

_MAX_BATCH = 100
_DOCUMENT_METADATA_KEY = "document"


class PineconeVectorStore(BaseVectorStore):
    def __init__(
        self,
        api_key: str,
        index_name: str,
        dimension: int,
        cloud: str = "aws",
        region: str = "us-east-1",
        metric: str = "cosine",
    ):
        try:
            from pinecone import Pinecone, ServerlessSpec
        except ImportError as e:
            raise VectorStoreError("pinecone-client is not installed. Run: pip install pinecone-client") from e

        self.index_name = index_name
        try:
            self._pc = Pinecone(api_key=api_key)
            existing = [idx["name"] for idx in self._pc.list_indexes()]
            if index_name not in existing:
                logger.info(f"Creating Pinecone index '{index_name}' (dim={dimension}, metric={metric})...")
                self._pc.create_index(
                    name=index_name,
                    dimension=dimension,
                    metric=metric,
                    spec=ServerlessSpec(cloud=cloud, region=region),
                )
            self._index = self._pc.Index(index_name)
            logger.info(f"Connected to Pinecone index '{index_name}'.")
        except Exception as e:
            raise VectorStoreError(f"Failed to initialize Pinecone index: {e}") from e

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
            vectors = []
            for doc_id, emb, doc_text, meta in zip(ids, embeddings, documents, metadatas):
                full_meta = dict(meta)
                full_meta[_DOCUMENT_METADATA_KEY] = doc_text
                vectors.append({"id": doc_id, "values": emb, "metadata": full_meta})

            for start in range(0, len(vectors), _MAX_BATCH):
                self._index.upsert(vectors=vectors[start:start + _MAX_BATCH])
            logger.info(f"Upserted {len(vectors)} vector(s) into Pinecone index '{self.index_name}'.")
        except Exception as e:
            raise VectorStoreError(f"Pinecone upsert failed: {e}") from e

    def query(
        self,
        query_embedding: List[float],
        top_k: int,
        where: Optional[Dict[str, Any]] = None,
    ) -> List[SearchMatch]:
        try:
            result = self._index.query(
                vector=query_embedding,
                top_k=top_k,
                include_metadata=True,
                filter=where or None,
            )
        except Exception as e:
            raise VectorStoreError(f"Pinecone query failed: {e}") from e

        matches: List[SearchMatch] = []
        for m in result.get("matches", []):
            metadata = dict(m.get("metadata", {}) or {})
            document = metadata.pop(_DOCUMENT_METADATA_KEY, "")
            score = float(m.get("score", 0.0))
            matches.append(
                SearchMatch(id=m["id"], document=document, metadata=metadata, score=max(0.0, min(1.0, score)))
            )
        return matches

    def count(self) -> int:
        try:
            stats = self._index.describe_index_stats()
            return int(stats.get("total_vector_count", 0))
        except Exception as e:
            raise VectorStoreError(f"Pinecone describe_index_stats failed: {e}") from e

    def delete_collection(self) -> None:
        try:
            self._pc.delete_index(self.index_name)
            logger.info(f"Deleted Pinecone index '{self.index_name}'.")
        except Exception as e:
            raise VectorStoreError(f"Failed to delete Pinecone index: {e}") from e
