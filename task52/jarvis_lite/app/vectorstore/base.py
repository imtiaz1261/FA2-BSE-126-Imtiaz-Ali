"""Shared vector store contract — Chroma and FAISS both implement this."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List

from app.chunking.chunker import DocumentChunk


@dataclass
class VectorSearchResult:
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    score: float = 0.0  # similarity, higher = more relevant (normalized where possible)


class BaseVectorStore(ABC):
    @abstractmethod
    def create_collection(self, name: str) -> None:
        """Idempotent — creates the collection if it doesn't already exist."""
        raise NotImplementedError

    @abstractmethod
    def add_chunks(self, chunks: List[DocumentChunk], embeddings: List[List[float]]) -> None:
        raise NotImplementedError

    @abstractmethod
    def similarity_search(self, query_embedding: List[float], top_k: int) -> List[VectorSearchResult]:
        raise NotImplementedError

    @abstractmethod
    def delete_collection(self, name: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def persist(self) -> None:
        """Flush to disk. No-op for stores that persist automatically."""
        raise NotImplementedError
