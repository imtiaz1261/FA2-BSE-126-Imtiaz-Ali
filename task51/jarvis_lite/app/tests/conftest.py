"""Shared pytest fixtures — a network-free stub embedding provider and
per-test isolated storage directories, since VECTOR_DB_PATH/UPLOAD_DIR
default to shared paths under the project root.
"""

from typing import List

import pytest

from app.config.settings import settings
from app.embeddings.base import BaseEmbeddingProvider


class DummyEmbeddingProvider(BaseEmbeddingProvider):
    """Deterministic, network-free embeddings for tests.

    Produces a small fixed-dimension vector derived from character
    codes so identical text always maps to the same vector and
    different text maps to different vectors — good enough to test
    the pipeline's plumbing without downloading a real model.
    """

    DIM = 16

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self._embed_one(t) for t in texts]

    def embed_query(self, text: str) -> List[float]:
        return self._embed_one(text)

    def _embed_one(self, text: str) -> List[float]:
        vector = [0.0] * self.DIM
        for i, char in enumerate(text or " "):
            vector[i % self.DIM] += ord(char) % 97
        norm = sum(v * v for v in vector) ** 0.5 or 1.0
        return [v / norm for v in vector]


@pytest.fixture
def dummy_embedding_provider() -> DummyEmbeddingProvider:
    return DummyEmbeddingProvider()


@pytest.fixture
def isolated_storage(tmp_path, monkeypatch):
    """Points VECTOR_DB_PATH and UPLOAD_DIR at a fresh tmp_path for this test."""
    monkeypatch.setattr(settings, "VECTOR_DB_PATH", str(tmp_path / "vector_db"))
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setattr(settings, "COLLECTION_NAME", "test_collection")
    return tmp_path
