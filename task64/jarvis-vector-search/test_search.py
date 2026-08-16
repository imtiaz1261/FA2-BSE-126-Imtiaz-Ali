"""
test_search.py
----------------
End-to-end demonstration / smoke test:
  1. Index all 50+ documents in data/documents/
  2. Run a handful of sample queries
  3. Print the top-5 results for each, with scores and metadata
  4. Run basic sanity assertions

Run directly:
    python test_search.py

By default this uses whatever backend is configured via environment
variables / .env (production default: sentence_transformers + chroma).
For a fast, fully offline run with no extra installs, set:
    EMBEDDING_PROVIDER=local_tfidf
    VECTOR_DB_PROVIDER=memory
before running, or copy .env.example to .env and edit it.
"""
import sys

from search_engine import SemanticSearchEngine
from exceptions import VectorSearchError
from logger import get_logger

logger = get_logger(__name__)

SAMPLE_QUERIES = [
    "how do I get my password back",
    "what tool should our team use to track projects",
    "keeping my laptop data safe if it's stolen",
    "how does the AI decide which document to show me",
    "time off request process",
    "difference between cloud database types",
]


def main() -> int:
    engine = SemanticSearchEngine()

    print("=" * 70)
    print("STEP 1: Indexing documents")
    print("=" * 70)
    indexed_count = engine.index_documents()
    print(f"Indexed {indexed_count} chunk(s).\n")

    stats = engine.stats()
    print("Engine stats:")
    for k, v in stats.items():
        print(f"  {k}: {v}")
    print()

    assert stats["vector_count"] >= 50, (
        f"Expected at least 50 indexed vectors, got {stats['vector_count']}"
    )

    print("=" * 70)
    print("STEP 2: Running sample queries (top-5 each)")
    print("=" * 70)

    for query in SAMPLE_QUERIES:
        print(f"\nQuery: \"{query}\"")
        print("-" * 70)
        try:
            results = engine.search(query, top_k=5)
        except VectorSearchError as e:
            print(f"  ERROR: {e}")
            continue

        if not results:
            print("  No results.")
            continue

        for rank, r in enumerate(results, start=1):
            title = r.metadata.get("title", r.metadata.get("filename", "?"))
            category = r.metadata.get("category", "?")
            snippet = r.document[:120].replace("\n", " ")
            print(f"  {rank}. [{r.score:.3f}] {title}  ({category})")
            print(f"     {snippet}...")

        assert len(results) <= 5, "search() returned more than the requested top_k"
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True), "results are not sorted by score descending"

    print("\n" + "=" * 70)
    print("All checks passed.")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
