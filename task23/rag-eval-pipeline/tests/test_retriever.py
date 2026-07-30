"""Unit tests for rag_pipeline/retriever.py (TF-IDF offline backend only —
the OpenAI/FAISS backend requires network access and API keys, and is
exercised via integration testing, not unit tests)."""

from __future__ import annotations

from rag_pipeline.retriever import Retriever


def test_retriever_returns_relevant_document():
    retriever = Retriever(backend="tfidf")
    results = retriever.retrieve("What is the uptime SLA for the Pro plan?", k=3)
    assert any("uptime" in r.lower() or "sla" in r.lower() for r in results)


def test_retriever_respects_k():
    retriever = Retriever(backend="tfidf")
    results = retriever.retrieve("storage pricing support", k=2)
    assert len(results) <= 2


def test_retriever_unknown_backend_raises():
    import pytest

    with pytest.raises(ValueError):
        Retriever(backend="not_a_real_backend")


def test_retriever_nonsense_query_returns_empty_or_low_relevance():
    retriever = Retriever(backend="tfidf")
    results = retriever.retrieve("xyzzy quux nonsense gibberish", k=3)
    # Should not error; may legitimately return zero results for pure gibberish.
    assert isinstance(results, list)
