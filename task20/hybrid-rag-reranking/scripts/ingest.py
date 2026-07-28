"""scripts/ingest.py — Builds both the BM25 and FAISS indexes from the
documents in data/documents/, and saves them to disk.

Run this once before querying or evaluating:

    python scripts/ingest.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import config  # noqa: E402
from src.bm25_retriever import BM25Retriever  # noqa: E402
from src.vector_retriever import VectorRetriever  # noqa: E402


def load_documents(directory: Path) -> dict[str, str]:
    """Loads every .txt file in the directory into a {filename: text} dict."""
    if not directory.exists():
        raise FileNotFoundError(f"Documents directory not found: {directory}")

    documents = {}
    for path in sorted(directory.glob("*.txt")):
        documents[path.name] = path.read_text(encoding="utf-8")

    if not documents:
        raise FileNotFoundError(f"No .txt documents found in {directory}")

    return documents


def main() -> None:
    print(f"Loading documents from: {config.DOCUMENTS_DIR}")
    documents = load_documents(config.DOCUMENTS_DIR)
    print(f"Loaded {len(documents)} documents.")

    print("\nBuilding BM25 index...")
    bm25 = BM25Retriever()
    bm25.build_index(documents)
    bm25.save(config.BM25_INDEX_PATH)
    print(f"BM25 index saved to: {config.BM25_INDEX_PATH}")

    print(f"\nBuilding vector index (downloading '{config.EMBEDDING_MODEL_NAME}' on first run)...")
    vector = VectorRetriever(config.EMBEDDING_MODEL_NAME)
    vector.build_index(documents)
    vector.save(config.FAISS_INDEX_PATH)
    print(f"Vector index saved to: {config.FAISS_INDEX_PATH}")

    print("\nIngestion complete. Ready to query or evaluate.")


if __name__ == "__main__":
    main()
