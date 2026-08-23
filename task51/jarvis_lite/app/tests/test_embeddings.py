"""Tests for the embedding layer.

The real providers (OpenAI, HuggingFace) need a network call or a
multi-hundred-MB model download, so they're covered here only by
contract tests against the `DummyEmbeddingProvider` fixture plus a
factory test that doesn't require actually loading a model.
"""

import pytest

from app.core.exceptions import EmbeddingError
from app.embeddings.openai_embeddings import OpenAIEmbeddingProvider


def test_dummy_provider_embed_documents_returns_one_vector_per_text(dummy_embedding_provider):
    vectors = dummy_embedding_provider.embed_documents(["hello", "world", "hello"])

    assert len(vectors) == 3
    assert all(len(v) == dummy_embedding_provider.DIM for v in vectors)
    # Identical text should embed identically (deterministic stub).
    assert vectors[0] == vectors[2]


def test_dummy_provider_embed_query_matches_embed_documents(dummy_embedding_provider):
    query_vector = dummy_embedding_provider.embed_query("search this")
    doc_vector = dummy_embedding_provider.embed_documents(["search this"])[0]

    assert query_vector == doc_vector


def test_dummy_provider_empty_batch_returns_empty_list(dummy_embedding_provider):
    assert dummy_embedding_provider.embed_documents([]) == []


def test_openai_provider_requires_api_key(monkeypatch):
    from app.config.settings import settings

    monkeypatch.setattr(settings, "OPENAI_API_KEY", "")

    with pytest.raises(EmbeddingError):
        OpenAIEmbeddingProvider()
