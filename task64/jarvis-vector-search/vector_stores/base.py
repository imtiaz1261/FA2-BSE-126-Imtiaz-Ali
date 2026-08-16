"""
vector_stores/base.py
------------------------
Abstract interface every vector database backend must implement.
Keeping this thin and provider-agnostic is what lets the search engine
swap between Chroma, Pinecone, or an in-memory store via one env var.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class SearchMatch:
    """A single semantic search result."""
    id: str
    document: str
    metadata: Dict[str, Any]
    score: float  # similarity score, 0..1, higher = more relevant


class BaseVectorStore(ABC):
    @abstractmethod
    def upsert(
        self,
        ids: List[str],
        embeddings: List[List[float]],
        documents: List[str],
        metadatas: List[Dict[str, Any]],
    ) -> None:
        """Insert or update vectors, in batches internally if needed."""
        raise NotImplementedError

    @abstractmethod
    def query(
        self,
        query_embedding: List[float],
        top_k: int,
        where: Optional[Dict[str, Any]] = None,
    ) -> List[SearchMatch]:
        """Return the top_k nearest matches to query_embedding, optionally
        filtered by an exact-match metadata filter (`where`)."""
        raise NotImplementedError

    @abstractmethod
    def count(self) -> int:
        """Number of vectors currently stored in the collection/index."""
        raise NotImplementedError

    @abstractmethod
    def delete_collection(self) -> None:
        """Drop the entire collection/index. Useful for re-indexing from scratch."""
        raise NotImplementedError
