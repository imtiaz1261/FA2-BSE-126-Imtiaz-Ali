"""
tests/test_pipeline.py
------------------------
Lightweight unit/integration tests for the semantic search pipeline.

Run with:
    pytest tests/ -v
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pytest

from src.preprocessing import clean_text, normalize_for_keyword_search, truncate_for_preview
from src.data_loader import load_documents
from src.embedding_generator import EmbeddingGenerator
from src.vector_store import VectorStore
from src.semantic_search import SemanticSearchEngine
from src.keyword_search import KeywordSearchEngine

DOCS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "documents")


def test_clean_text_collapses_whitespace():
    assert clean_text("Hello    world \n\n  foo") == "Hello world foo"


def test_clean_text_handles_empty():
    assert clean_text("") == ""
    assert clean_text(None) == ""


def test_normalize_for_keyword_search_strips_punct_and_lowers():
    result = normalize_for_keyword_search("Hello, World! This is GREAT.")
    assert result == "hello world this is great"


def test_truncate_for_preview_short_text_unchanged():
    text = "short text"
    assert truncate_for_preview(text, max_chars=100) == text


def test_truncate_for_preview_long_text_truncated():
    text = "word " * 100
    preview = truncate_for_preview(text, max_chars=50)
    assert len(preview) <= 53  # allow for the "..." suffix
    assert preview.endswith("...")


def test_load_documents_returns_100():
    docs = load_documents(DOCS_DIR)
    assert len(docs) == 100
    assert all(doc.raw_text.strip() for doc in docs)


def test_load_documents_parses_metadata_header():
    docs = load_documents(DOCS_DIR)
    doc = docs[0]
    assert doc.title is not None
    assert doc.category is not None


@pytest.fixture(scope="module")
def small_corpus():
    return [
        "The cat sat on the mat and purred softly.",
        "Dogs are loyal companions and love to play fetch.",
        "The stock market rallied today on strong earnings.",
        "Investors are watching interest rate decisions closely.",
        "A new species of frog was discovered in the rainforest.",
    ]


def test_embedding_generator_fallback_produces_normalized_vectors(small_corpus):
    generator = EmbeddingGenerator(force_fallback=True, embedding_dim_fallback=3)
    embeddings = generator.get_or_create_embeddings(small_corpus, cache_name="test_cache", show_progress=False)
    assert embeddings.shape[0] == len(small_corpus)
    norms = np.linalg.norm(embeddings, axis=1)
    assert np.allclose(norms, 1.0, atol=1e-5)


def test_vector_store_faiss_returns_top_k(small_corpus):
    generator = EmbeddingGenerator(force_fallback=True, embedding_dim_fallback=3)
    embeddings = generator.get_or_create_embeddings(small_corpus, cache_name="test_cache_2", show_progress=False)

    store = VectorStore(backend="faiss")
    metadatas = [{"doc_id": i, "title": t, "category": "test", "preview": t} for i, t in enumerate(small_corpus)]
    store.add(embeddings, metadatas)

    query_embedding = generator.encode(["Tell me about finance and the stock market"])[0]
    results = store.search(query_embedding, top_k=2)

    assert len(results) == 2
    assert results[0]["score"] >= results[1]["score"]


def test_semantic_search_engine_end_to_end(small_corpus):
    generator = EmbeddingGenerator(force_fallback=True, embedding_dim_fallback=3)
    embeddings = generator.get_or_create_embeddings(small_corpus, cache_name="test_cache_3", show_progress=False)

    store = VectorStore(backend="faiss")
    metadatas = [{"doc_id": i, "title": t, "category": "test", "preview": t} for i, t in enumerate(small_corpus)]
    store.add(embeddings, metadatas)

    engine = SemanticSearchEngine(generator, store)
    outcome = engine.search("pets and animals", top_k=3)

    assert outcome["query"] == "pets and animals"
    assert len(outcome["results"]) == 3
    assert outcome["latency_ms"] >= 0


def test_keyword_search_engine_finds_exact_match(small_corpus):
    metadatas = [{"doc_id": i, "title": t, "category": "test", "preview": t} for i, t in enumerate(small_corpus)]
    engine = KeywordSearchEngine()
    engine.fit(small_corpus, metadatas)

    results = engine.search("interest rate decisions", top_k=2)
    assert len(results) >= 1
    assert "interest" in results[0]["metadata"]["preview"].lower()


def test_vector_store_category_filter(small_corpus):
    generator = EmbeddingGenerator(force_fallback=True, embedding_dim_fallback=3)
    embeddings = generator.get_or_create_embeddings(small_corpus, cache_name="test_cache_4", show_progress=False)

    store = VectorStore(backend="faiss")
    categories = ["animal", "animal", "finance", "finance", "nature"]
    metadatas = [
        {"doc_id": i, "title": t, "category": c, "preview": t}
        for i, (t, c) in enumerate(zip(small_corpus, categories))
    ]
    store.add(embeddings, metadatas)

    query_embedding = generator.encode(["market news"])[0]
    results = store.search(query_embedding, top_k=5, category_filter="finance")
    assert all(r["metadata"]["category"] == "finance" for r in results)
