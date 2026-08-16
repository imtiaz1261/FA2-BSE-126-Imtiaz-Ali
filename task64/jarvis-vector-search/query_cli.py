"""
query_cli.py
-------------
Interactive command-line search against the already-indexed collection.
Run test_search.py (or your own indexing call) at least once first.

Usage:
    python query_cli.py
    python query_cli.py --top_k 3
    python query_cli.py --category "IT & Security"
"""
import argparse

from search_engine import SemanticSearchEngine
from exceptions import VectorSearchError


def main():
    parser = argparse.ArgumentParser(description="Query the Jarvis-Lite knowledge base")
    parser.add_argument("--top_k", type=int, default=None, help="Number of results (default from config)")
    parser.add_argument("--category", type=str, default=None, help="Filter results to an exact category")
    args = parser.parse_args()

    engine = SemanticSearchEngine()
    stats = engine.stats()
    print(f"Connected. {stats['vector_count']} vector(s) indexed "
          f"({stats['embedding_provider']} / {stats['vector_db_provider']}).")
    if stats["vector_count"] == 0:
        print("Index is empty — run test_search.py or call engine.index_documents() first.")
        return

    print("Type a question, or 'quit' to exit.\n")
    filters = {"category": args.category} if args.category else None

    while True:
        try:
            query = input("ask> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if query.lower() in ("quit", "exit", "q"):
            break
        if not query:
            continue

        try:
            results = engine.search(query, top_k=args.top_k, filters=filters)
        except VectorSearchError as e:
            print(f"  Error: {e}\n")
            continue

        if not results:
            print("  No results.\n")
            continue

        for i, r in enumerate(results, start=1):
            title = r.metadata.get("title", r.metadata.get("filename", "?"))
            category = r.metadata.get("category", "?")
            print(f"  {i}. [{r.score:.3f}] {title}  ({category})")
            print(f"     {r.document[:160]}")
        print()


if __name__ == "__main__":
    main()
