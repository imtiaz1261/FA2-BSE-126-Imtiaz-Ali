"""
embeddings/base.py
-------------------
Abstract interface every embedding provider must implement, so the
rest of the system (vector store, search engine) never needs to know
which concrete embedding backend is in use.
"""
from abc import ABC, abstractmethod
from typing import List


class BaseEmbeddingProvider(ABC):
    """Common interface for all embedding backends."""

    #: Human-readable name of the underlying model, used in logs/metadata.
    model_name: str = "unknown"

    @abstractmethod
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed a batch of documents. Returns one vector per input text, same order."""
        raise NotImplementedError

    @abstractmethod
    def embed_query(self, text: str) -> List[float]:
        """Embed a single query string."""
        raise NotImplementedError

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Vector dimensionality produced by this provider."""
        raise NotImplementedError
