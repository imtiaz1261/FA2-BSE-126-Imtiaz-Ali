"""
search_engine.py
------------------
Public entry point for the Jarvis-Lite vector search module.
Wires together: config -> embedding provider -> vector store, and
exposes two operations the rest of the app needs:

    engine = SemanticSearchEngine()
    engine.index_documents("data/documents")
    results = engine.search("how do I reset my password?", top_k=5)

`results` is a list of SearchResult, each with .document, .score
(0..1, higher = more relevant), and .metadata (doc_id, filename,
source, title, category, chunk_index, ...).
"""
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from config import Config, load_config
from document_loader import load_documents, validate_chunks, Chunk
from embeddings import get_embedding_provider
from embeddings.base import BaseEmbeddingProvider
from vector_stores import get_vector_store
from vector_stores.base import BaseVectorStore
from exceptions import ValidationError, VectorSearchError
from logger import get_logger

logger = get_logger(__name__)


@dataclass
class SearchResult:
    document: str
    score: float
    metadata: Dict[str, Any]

    def __repr__(self) -> str:
        title = self.metadata.get("title", "")
        return f"SearchResult(score={self.score:.3f}, title={title!r})"


class SemanticSearchEngine:
    def __init__(self, config: Optional[Config] = None):
        self.config = config or load_config()
        logger.info(
            f"Initializing SemanticSearchEngine "
            f"(embedding_provider={self.config.embedding_provider}, "
            f"vector_db={self.config.vector_db_provider}, top_k={self.config.top_k})"
        )
        self.embedding_provider: BaseEmbeddingProvider = get_embedding_provider(self.config)
        self.vector_store: BaseVectorStore = get_vector_store(
            self.config, embedding_dimension=self.embedding_provider.dimension
        )

    # ------------------------------------------------------------------ #
    # Indexing
    # ------------------------------------------------------------------ #
    def index_documents(self, directory: Optional[str] = None) -> int:
        """
        Load documents from `directory` (defaults to config.documents_dir),
        embed them, and upsert into the vector store.

        Returns the number of chunks indexed.
        """
        directory = directory or self.config.documents_dir
        chunks: List[Chunk] = load_documents(
            directory,
            chunk_size=self.config.chunk_size,
            chunk_overlap=self.config.chunk_overlap,
        )
        validate_chunks(chunks)
        return self.index_chunks(chunks)

    def index_chunks(self, chunks: List[Chunk]) -> int:
        if not chunks:
            raise ValidationError("index_chunks called with an empty list.")

        texts = [c.text for c in chunks]
        ids = [c.id for c in chunks]
        metadatas = [self._enrich_metadata(c.metadata) for c in chunks]

        batch_size = self.config.batch_size
        total = 0
        for start in range(0, len(chunks), batch_size):
            end = start + batch_size
            batch_texts = texts[start:end]
            batch_embeddings = self.embedding_provider.embed_documents(batch_texts)
            self.vector_store.upsert(
                ids=ids[start:end],
                embeddings=batch_embeddings,
                documents=batch_texts,
                metadatas=metadatas[start:end],
            )
            total += len(batch_texts)
            logger.info(f"Indexed {total}/{len(chunks)} chunk(s)...")

        logger.info(f"Indexing complete. Vector store now has {self.vector_store.count()} vector(s).")
        return total

    def _enrich_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        clean = dict(metadata)
        clean["embedding_model"] = self.embedding_provider.model_name
        return clean

    # ------------------------------------------------------------------ #
    # Searching
    # ------------------------------------------------------------------ #
    def search(
        self,
        query: str,
        top_k: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None,
        min_score: Optional[float] = None,
    ) -> List[SearchResult]:
        """
        Semantic search over the indexed collection.

        query: natural-language search string (required, non-empty)
        top_k: number of results to return (defaults to config.top_k)
        filters: optional exact-match metadata filter, e.g. {"category": "IT & Security"}
        min_score: drop results below this similarity score (defaults to config.min_score)
        """
        self._validate_query(query)
        top_k = top_k or self.config.top_k
        min_score = self.config.min_score if min_score is None else min_score

        if self.vector_store.count() == 0:
            logger.warning("search() called but the vector store is empty. Call index_documents() first.")
            return []

        try:
            query_embedding = self.embedding_provider.embed_query(query)
            matches = self.vector_store.query(query_embedding, top_k=top_k, where=filters)
        except VectorSearchError:
            raise
        except Exception as e:
            raise VectorSearchError(f"Unexpected error during search: {e}") from e

        results = [
            SearchResult(document=m.document, score=m.score, metadata=m.metadata)
            for m in matches
            if m.score >= min_score
        ]
        logger.info(f"Query '{query[:60]}' -> {len(results)} result(s) (top_k={top_k}).")
        return results

    @staticmethod
    def _validate_query(query: str) -> None:
        if query is None or not isinstance(query, str) or not query.strip():
            raise ValidationError("Query must be a non-empty string.")
        if len(query) > 2000:
            raise ValidationError("Query is too long (max 2000 characters).")

    # ------------------------------------------------------------------ #
    # Maintenance
    # ------------------------------------------------------------------ #
    def reset_index(self) -> None:
        """Delete and recreate the collection/index — use before a full re-index."""
        self.vector_store.delete_collection()
        self.vector_store = get_vector_store(self.config, embedding_dimension=self.embedding_provider.dimension)

    def stats(self) -> Dict[str, Any]:
        return {
            "vector_count": self.vector_store.count(),
            "embedding_provider": self.config.embedding_provider,
            "embedding_model": self.embedding_provider.model_name,
            "embedding_dimension": self.embedding_provider.dimension,
            "vector_db_provider": self.config.vector_db_provider,
            "collection_name": self.config.collection_name,
        }
