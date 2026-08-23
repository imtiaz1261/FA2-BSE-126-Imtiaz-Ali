"""End-to-end tests: retriever -> prompt builder -> RAGService,
using the dummy embedding provider and FAISS so no network or API
key is required. The LLM generation call itself is monkeypatched.
"""

import pytest

from app.retriever.retriever import Retriever
from app.rag.prompt_builder import build_prompt
from app.rag.rag_service import RAGService


def _build_populated_faiss_store(isolated_storage, dummy_embedding_provider):
    from app.chunking.chunker import DocumentChunk
    from app.vectorstore.faiss_store import FAISSVectorStore

    store = FAISSVectorStore()
    chunks = [
        DocumentChunk(
            chunk_id="c1",
            content="The refund policy allows returns within 30 days of purchase.",
            metadata={"document_name": "policy.txt", "chunk_id": "c1", "page": 1},
        ),
        DocumentChunk(
            chunk_id="c2",
            content="Shipping usually takes 3 to 5 business days.",
            metadata={"document_name": "policy.txt", "chunk_id": "c2", "page": 2},
        ),
    ]
    embeddings = dummy_embedding_provider.embed_documents([c.content for c in chunks])
    store.add_chunks(chunks, embeddings)
    return store


def test_retriever_returns_relevant_chunks(isolated_storage, dummy_embedding_provider):
    pytest.importorskip("faiss")
    store = _build_populated_faiss_store(isolated_storage, dummy_embedding_provider)
    retriever = Retriever(vector_store=store, embedding_provider=dummy_embedding_provider)

    results = retriever.retrieve("What is the refund policy?", top_k=2)

    assert len(results) == 2
    assert all(r.content for r in results)


def test_build_prompt_includes_numbered_context_and_question(isolated_storage, dummy_embedding_provider):
    pytest.importorskip("faiss")
    store = _build_populated_faiss_store(isolated_storage, dummy_embedding_provider)
    retriever = Retriever(vector_store=store, embedding_provider=dummy_embedding_provider)
    chunks = retriever.retrieve("refund policy", top_k=2)

    messages = build_prompt("What is the refund policy?", chunks)

    assert messages[0]["role"] == "system"
    assert "[1]" in messages[1]["content"]
    assert "What is the refund policy?" in messages[1]["content"]


def test_rag_service_query_returns_expected_shape(isolated_storage, dummy_embedding_provider, monkeypatch):
    pytest.importorskip("faiss")
    store = _build_populated_faiss_store(isolated_storage, dummy_embedding_provider)
    retriever = Retriever(vector_store=store, embedding_provider=dummy_embedding_provider)
    service = RAGService(retriever=retriever)

    # No OpenAI key in tests — stub the generation step directly.
    monkeypatch.setattr(service, "_generate", lambda messages: "Refunds are accepted within 30 days. [1]")

    result = service.query("What is the refund policy?", top_k=2)

    assert result["answer"] == "Refunds are accepted within 30 days. [1]"
    assert len(result["sources"]) >= 1
    assert len(result["retrieved_chunks"]) == 2
    assert result["retrieved_chunks"][0]["score"] >= result["retrieved_chunks"][-1]["score"]


def test_rag_service_query_with_no_matches_returns_fallback_answer(isolated_storage, dummy_embedding_provider):
    pytest.importorskip("faiss")
    from app.vectorstore.faiss_store import FAISSVectorStore

    empty_store = FAISSVectorStore()  # nothing ingested
    retriever = Retriever(vector_store=empty_store, embedding_provider=dummy_embedding_provider)
    service = RAGService(retriever=retriever)

    result = service.query("Anything at all?")

    assert result["sources"] == []
    assert result["retrieved_chunks"] == []
    assert "don't have" in result["answer"].lower()
