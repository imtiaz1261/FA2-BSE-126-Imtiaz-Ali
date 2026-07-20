"""
app.py
--------
Main entry point for the Semantic Document Search application.

Workflow:
    1. If a FAISS index already exists in faiss_index/, load it.
    2. Otherwise (or if --rebuild is passed), run the ingest pipeline
       (load -> chunk -> embed -> save index) automatically.
    3. Accept user queries from the terminal in a loop.
    4. For each query: embed it, run FAISS similarity search, display
       the Top-K most relevant chunks (document, page, score, text).
    5. If nothing relevant is found, display "No relevant information found."
    6. Continue until the user exits.

Run:
    python app.py
    python app.py --rebuild            # force re-ingest even if an index exists
    python app.py --top-k 3            # change default Top-K
    python app.py --force-fallback     # no internet? use offline embeddings
"""

from __future__ import annotations

import argparse
import logging
import os
import sys

from dotenv import load_dotenv

from embeddings import get_embedding_model
from ingest import run_ingest_pipeline
from search import load_faiss_index, search_query
from utils import print_banner, print_search_results, setup_logging

load_dotenv()  # load OPENAI_API_KEY etc. from a local .env file, if present

logger = logging.getLogger("semantic-search.app")


def get_or_build_index(args, embedding_model):
    """
    Load the FAISS index from disk if it exists (and --rebuild wasn't
    passed); otherwise build it from scratch via the ingest pipeline.
    """
    index_file = os.path.join(args.index_dir, "index.faiss")
    index_exists = os.path.exists(index_file)

    if index_exists and not args.rebuild:
        logger.info("Existing FAISS index found — loading it (use --rebuild to regenerate).")
        return load_faiss_index(args.index_dir, embedding_model)

    logger.info("No usable index found (or --rebuild requested). Building a new one...")
    return run_ingest_pipeline(
        data_dir=args.data_dir,
        index_dir=args.index_dir,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
        force_fallback=args.force_fallback,
        use_openai=args.use_openai,
    )


def interactive_loop(vectorstore, top_k: int):
    print_banner("Semantic Document Search using FAISS")
    print("Type a natural-language query and press Enter.")
    print("Commands:")
    print("  :k <N>       change number of results returned (Top-K)")
    print("  :exit/:quit  leave the application")
    print("=" * 64)

    while True:
        try:
            query = input("\nSearch> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting. Goodbye!")
            break

        if not query:
            continue
        if query.lower() in {":exit", ":quit"}:
            print("Exiting. Goodbye!")
            break
        if query.lower().startswith(":k "):
            try:
                top_k = max(1, int(query.split()[1]))
                print(f"Top-K set to {top_k}")
            except (IndexError, ValueError):
                print("Usage: :k <number>")
            continue

        try:
            results = search_query(vectorstore, query, top_k=top_k)
            print_search_results(query, results)
        except ValueError as exc:
            # Invalid query (e.g. empty) — show the message and keep looping
            print(f"[Error] {exc}")
        except Exception as exc:  # noqa: BLE001 - never let one bad query crash the app
            logger.error("Unexpected error during search: %s", exc)
            print("[Error] Something went wrong while searching. Please try again.")


def main():
    parser = argparse.ArgumentParser(description="Semantic Document Search using FAISS")
    parser.add_argument(
        "--data-dir", default="data", help="Folder containing .pdf / .txt files")
    parser.add_argument(
        "--index-dir", default="faiss_index", help="Folder for the saved FAISS index")
    parser.add_argument(
        "--chunk-size", type=int, default=1000, help="Chunk size in characters")
    parser.add_argument(
        "--chunk-overlap", type=int, default=200, help="Chunk overlap in characters")
    parser.add_argument(
        "--top-k", type=int, default=5, help="Default number of results per query")
    parser.add_argument(
        "--rebuild", action="store_true",
        help="Force rebuilding the index even if one exists")
    parser.add_argument(
        "--force-fallback", action="store_true",
        help="Force offline TF-IDF+SVD embeddings")
    parser.add_argument(
        "--use-openai", action="store_true",
        help="Use OpenAI embeddings instead of sentence-transformers")
    parser.add_argument(
        "--query", default=None,
        help="Run a single query non-interactively and exit")
    args = parser.parse_args()

    setup_logging()

    try:
        embedding_model = get_embedding_model(
            index_dir=args.index_dir, force_fallback=args.force_fallback, use_openai=args.use_openai
        )
        vectorstore = get_or_build_index(args, embedding_model)
    except (FileNotFoundError, ValueError, EnvironmentError) as exc:
        logger.error(str(exc))
        sys.exit(1)

    if args.query:
        results = search_query(vectorstore, args.query, top_k=args.top_k)
        print_search_results(args.query, results)
        return

    interactive_loop(vectorstore, top_k=args.top_k)


if __name__ == "__main__":
    main()