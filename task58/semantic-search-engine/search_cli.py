"""
search_cli.py
-------------
Interactive command-line semantic search over data/products.csv
(or any CSV you point it at).

Usage:
    python search_cli.py
    python search_cli.py --csv data/products.csv --top_k 5
    python search_cli.py --backend embeddings   # needs sentence-transformers
"""
import argparse
from pathlib import Path

from semantic_search import SemanticSearchEngine


def main():
    parser = argparse.ArgumentParser(description="Semantic search over a CSV dataset")
    parser.add_argument("--csv", default="data/products.csv", help="Path to CSV dataset")
    parser.add_argument("--top_k", type=int, default=5, help="Number of results to show")
    parser.add_argument(
        "--backend",
        choices=["lsa", "embeddings"],
        default="lsa",
        help="'lsa' works offline (default). 'embeddings' needs "
             "`pip install sentence-transformers` and downloads a model on first use.",
    )
    args = parser.parse_args()

    csv_path = Path(args.csv)
    if not csv_path.exists():
        print(f"Could not find {csv_path}. Run: python data/generate_dataset.py")
        return

    print(f"Loading '{csv_path}' and building the {args.backend} index...")
    engine = SemanticSearchEngine.from_csv(str(csv_path), backend=args.backend)
    print(f"Indexed {len(engine.records)} records. Type a query (or 'quit' to exit).\n")

    while True:
        try:
            query = input("search> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if query.lower() in ("quit", "exit", "q"):
            break
        if not query:
            continue

        results = engine.search(query, top_k=args.top_k)
        if not results:
            print("  No results.\n")
            continue
        for i, r in enumerate(results, start=1):
            name = r.row.get("name", "")
            desc = r.row.get("description", "")
            print(f"  {i}. [{r.score:.3f}] {name}")
            print(f"     {desc}")
        print()


if __name__ == "__main__":
    main()
