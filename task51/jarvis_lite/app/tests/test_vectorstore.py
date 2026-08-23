"""Tests for the vector store backends.

Both Chroma and FAISS run fully locally (no network), but require
their packages to be installed — skipped automatically if not, so
the suite still runs for whichever backend(s) you have set up.
"""

import pytest

from app.chunking.chunker import DocumentChunk


def _sample_chunks():
    return [
        DocumentChunk(chunk_id="c1", content="Cats are small domesticated felines.", metadata={"document_name": "pets.txt", "chunk_id": "c1"}),
        DocumentChunk(chunk_id="c2", content="The stock market fell sharply today.", metadata={"document_name": "news.txt", "chunk_id": "c2"}),
    ]


def test_faiss_store_add_and_search(isolated_storage, dummy_embedding_provider):
    pytest.importorskip("faiss")
    from app.vectorstore.faiss_store import FAISSVectorStore

    store = FAISSVectorStore()
    chunks = _sample_chunks()
    embeddings = dummy_embedding_provider.embed_documents([c.content for c in chunks])

    store.add_chunks(chunks, embeddings)

    query_embedding = dummy_embedding_provider.embed_query("Tell me about cats")
    results = store.similarity_search(query_embedding, top_k=2)

    assert len(results) == 2
    assert results[0].metadata["document_name"] in {"pets.txt", "news.txt"}


def test_faiss_store_persists_across_instances(isolated_storage, dummy_embedding_provider):
    pytest.importorskip("faiss")
    from app.vectorstore.faiss_store import FAISSVectorStore

    chunks = _sample_chunks()
    embeddings = dummy_embedding_provider.embed_documents([c.content for c in chunks])

    store = FAISSVectorStore()
    store.add_chunks(chunks, embeddings)

    reloaded = FAISSVectorStore()
    results = reloaded.similarity_search(embeddings[0], top_k=2)

    assert len(results) == 2


def test_chroma_store_add_and_search(isolated_storage, dummy_embedding_provider):
    pytest.importorskip("chromadb")
    from app.vectorstore.chroma_store import ChromaVectorStore

    store = ChromaVectorStore()
    chunks = _sample_chunks()
    embeddings = dummy_embedding_provider.embed_documents([c.content for c in chunks])

    store.add_chunks(chunks, embeddings)

    query_embedding = dummy_embedding_provider.embed_query("Tell me about cats")
    results = store.similarity_search(query_embedding, top_k=2)

    assert len(results) == 2


def test_vector_store_rejects_mismatched_lengths(isolated_storage, dummy_embedding_provider):
    pytest.importorskip("faiss")
    from app.core.exceptions import VectorStoreError
    from app.vectorstore.faiss_store import FAISSVectorStore

    store = FAISSVectorStore()
    chunks = _sample_chunks()

    with pytest.raises(VectorStoreError):
        store.add_chunks(chunks, [[0.1, 0.2]])  # only one embedding for two chunks
