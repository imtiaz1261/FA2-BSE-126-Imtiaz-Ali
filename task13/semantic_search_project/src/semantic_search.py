"""
semantic_search.py
---------------------
High-level Semantic Search Engine that ties together:
    - EmbeddingGenerator (query -> vector)
    - VectorStore (top-K similarity search)

Also measures and reports search latency (bonus feature).
"""

from __future__ import annotations

import time
import logging
from typing import List, Dict, Any, Optional

from .embedding_generator import EmbeddingGenerator
from .vector_store import VectorStore

logger = logging.getLogger(__name__)


class SemanticSearchEngine:
    def __init__(self, embedding_generator: EmbeddingGenerator, vector_store: VectorStore):
        self.embedding_generator = embedding_generator
        self.vector_store = vector_store

    def search(
        self, query: str, top_k: int = 5, category_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Run a semantic search for `query` and return results plus timing
        information.

        Returns:
            {
                "query": str,
                "results": [{"score": float, "metadata": {...}}, ...],
                "latency_ms": float,
            }
        """
        start = time.perf_counter()

        query_embedding = self.embedding_generator.encode([query])[0]
        results = self.vector_store.search(
            query_embedding, top_k=top_k, category_filter=category_filter
        )

        latency_ms = (time.perf_counter() - start) * 1000
        return {"query": query, "results": results, "latency_ms": latency_ms}
