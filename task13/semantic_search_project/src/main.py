"""
main.py
---------
Entry point for the Semantic Search CLI application.

Pipeline:
    1. Load documents from data/documents/
    2. Preprocess / clean text
    3. Generate (or load cached) embeddings
    4. Build a vector store index
    5. Fit a keyword-search baseline (bonus, for comparison)
    6. Loop: accept user queries from the terminal, run semantic search,
       display Top-K results with doc id / score / preview, until the
       user exits.

Run from the project root:
    python -m src.main
or:
    python src/main.py
"""

from __future__ import annotations

import argparse
import logging
import os
import sys

# Allow running as `python src/main.py` as well as `python -m src.main`
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data_loader import load_documents
from src.preprocessing import preprocess_documents, truncate_for_preview
from src.embedding_generator import EmbeddingGenerator
from src.vector_store import VectorStore
from src.semantic_search import SemanticSearchEngine
from src.keyword_search import KeywordSearchEngine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("main")

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DOCS_DIR = os.path.join(PROJECT_ROOT, "data", "documents")


def build_pipeline(docs_dir: str, backend: str, model_name: str, force_fallback: bool):
    """Run steps 1-5 of the pipeline and return the ready-to-query engines."""

    logger.info("Step 1/5: Loading documents from %s", docs_dir)
    documents = load_documents(docs_dir)
    logger.info("Loaded %d documents", len(documents))

    logger.info("Step 2/5: Preprocessing documents")
    documents = preprocess_documents(documents)

    logger.info("Step 3/5: Generating embeddings (this may take a moment the first time)")
    embedder = EmbeddingGenerator(model_name=model_name, force_fallback=force_fallback)
    clean_texts = [doc.metadata["clean_text"] for doc in documents]
    embeddings = embedder.get_or_create_embeddings(clean_texts, cache_name="doc_embeddings")
    logger.info("Embeddings ready | backend=%s | dim=%d", embedder.backend_name, embedder.embedding_dim)

    logger.info("Step 4/5: Building vector store (%s)", backend)
    store = VectorStore(backend=backend)
    metadatas = [
        {
            "doc_id": doc.doc_id,
            "filename": doc.filename,
            "title": doc.title,
            "category": doc.category or "uncategorized",
            "preview": truncate_for_preview(doc.metadata["clean_text"]),
        }
        for doc in documents
    ]
    store.add(embeddings, metadatas)

    logger.info("Step 5/5: Fitting keyword-search baseline (for comparison)")
    keyword_engine = KeywordSearchEngine()
    keyword_engine.fit(clean_texts, metadatas)

    semantic_engine = SemanticSearchEngine(embedder, store)
    return semantic_engine, keyword_engine, documents


def print_results(title: str, results, latency_ms: float | None = None):
    print(f"\n{title}")
    print("-" * len(title))
    if not results:
        print("  No results found.")
        return
    for rank, r in enumerate(results, start=1):
        meta = r["metadata"]
        print(f"  #{rank}  Doc ID: {meta['doc_id']:<4} Score: {r['score']:.4f}  "
              f"Category: {meta['category']}")
        print(f"       Title:   {meta['title']}")
        print(f"       Preview: {meta['preview']}")
    if latency_ms is not None:
        print(f"\n  Search latency: {latency_ms:.2f} ms")


def interactive_loop(semantic_engine: SemanticSearchEngine, keyword_engine: KeywordSearchEngine, top_k: int):
    print("\n" + "=" * 60)
    print(" Semantic Search Engine — 100 Document Collection")
    print("=" * 60)
    print("Type a natural-language query and press Enter.")
    print("Commands:")
    print("  :k <N>            set number of results to return (Top-K)")
    print("  :filter <category> filter results by category (blank to clear)")
    print("  :compare          toggle showing keyword-search results too")
    print("  :exit / :quit     leave the application")
    print("=" * 60)

    category_filter = None
    show_compare = False

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
        if query.lower().startswith(":filter"):
            parts = query.split(maxsplit=1)
            category_filter = parts[1].strip() if len(parts) > 1 and parts[1].strip() else None
            print(f"Category filter set to: {category_filter or '(none)'}")
            continue
        if query.lower() == ":compare":
            show_compare = not show_compare
            print(f"Keyword-search comparison: {'ON' if show_compare else 'OFF'}")
            continue

        try:
            outcome = semantic_engine.search(query, top_k=top_k, category_filter=category_filter)
            print_results("Semantic Search Results", outcome["results"], outcome["latency_ms"])

            if show_compare:
                kw_results = keyword_engine.search(query, top_k=top_k)
                print_results("Keyword (TF-IDF) Search Results", kw_results)
        except Exception as exc:  # noqa: BLE001
            logger.error("Search failed: %s", exc)
            print(f"  [Error] Search failed: {exc}")


def main():
    parser = argparse.ArgumentParser(description="Semantic Search Engine over 100 documents")
    parser.add_argument("--docs-dir", default=DEFAULT_DOCS_DIR, help="Directory containing documents")
    parser.add_argument("--backend", default="faiss", choices=["faiss", "chroma"], help="Vector store backend")
    parser.add_argument("--model", default="all-MiniLM-L6-v2", help="Sentence-transformers model name")
    parser.add_argument("--top-k", type=int, default=5, help="Number of results to return per query")
    parser.add_argument(
        "--force-fallback",
        action="store_true",
        help="Force the offline TF-IDF+SVD embedding backend instead of sentence-transformers",
    )
    parser.add_argument("--query", default=None, help="Run a single query non-interactively and exit")
    args = parser.parse_args()

    try:
        semantic_engine, keyword_engine, documents = build_pipeline(
            args.docs_dir, args.backend, args.model, args.force_fallback
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to initialize pipeline: %s", exc)
        sys.exit(1)

    if args.query:
        outcome = semantic_engine.search(args.query, top_k=args.top_k)
        print_results(f"Semantic Search Results for: '{args.query}'", outcome["results"], outcome["latency_ms"])
        return

    interactive_loop(semantic_engine, keyword_engine, top_k=args.top_k)


if __name__ == "__main__":
    main()
