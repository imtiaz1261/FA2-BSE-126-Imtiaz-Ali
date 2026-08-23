"""Retrieval engine: embeds a query and fetches the top-k most similar chunks."""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from app.config.settings import settings
from app.core.exceptions import RetrievalError
from app.embeddings.base import BaseEmbeddingProvider
from app.embeddings.embedding_factory import get_embedding_provider
from app.vectorstore.base import BaseVectorStore
from app.vectorstore.vectorstore_factory import get_vector_store

logger = logging.getLogger(__name__)


@dataclass
class RetrievedChunk:
    content: str
    metadata: Dict[str, Any]
    score: float


class Retriever:
    def __init__(
        self,
        vector_store: Optional[BaseVectorStore] = None,
        embedding_provider: Optional[BaseEmbeddingProvider] = None,
    ) -> None:
        self._vector_store = vector_store or get_vector_store()
        self._embedding_provider = embedding_provider or get_embedding_provider()

    def retrieve(self, query: str, top_k: Optional[int] = None) -> List[RetrievedChunk]:
        if not query or not query.strip():
            raise RetrievalError("Query must not be empty.")

        k = top_k or settings.RETRIEVAL_TOP_K
        query_embedding = self._embedding_provider.embed_query(query)

        results = self._vector_store.similarity_search(query_embedding, k)
        logger.info("Retrieved %d chunk(s) for query: %r", len(results), query[:80])

        return [RetrievedChunk(content=r.content, metadata=r.metadata, score=r.score) for r in results]
