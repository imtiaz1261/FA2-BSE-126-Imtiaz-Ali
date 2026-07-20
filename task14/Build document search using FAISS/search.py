"""
search.py
-----------
Loads the previously saved FAISS index and performs semantic similarity
search against it.

Pipeline:
    1. load_faiss_index()  - load the persisted FAISS index + docstore
    2. search_query()      - embed the query, run similarity search,
                              return the Top-K most relevant chunks with
                              a normalized similarity score, source
                              document name, and page number

Run directly for a quick one-off query:
    python search.py --query "what is semantic search" --top-k 5
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from typing import List, Optional

from langchain_community.vectorstores import FAISS

from embeddings import get_embedding_model
from utils import print_search_results, setup_logging, validate_query

logger = logging.getLogger("semantic-search.search")

DEFAULT_TOP_K = 5


def load_faiss_index(index_dir: str, embedding_model) -> FAISS:
    """
    Load a FAISS index previously saved by ingest.py.

    Raises:
        FileNotFoundError: if the index folder / files don't exist, with
        a clear message telling the user to run ingest.py first.
    """
    index_file = os.path.join(index_dir, "index.faiss")
    if not os.path.isdir(index_dir) or not os.path.exists(index_file):
        raise FileNotFoundError(
            f"No FAISS index found at '{index_dir}'. "
            f"Run 'python ingest.py' first to build the index from your documents."
        )

    # allow_dangerous_deserialization=True is required by LangChain because
    # loading a FAISS index unpickles the docstore. This is safe here since
    # we are only ever loading an index WE created locally via ingest.py.
    vectorstore = FAISS.load_local(
        index_dir, embedding_model, allow_dangerous_deserialization=True
    )
    logger.info("Loaded FAISS index from '%s' (%d vectors)", index_dir, vectorstore.index.ntotal)
    return vectorstore


def _l2_distance_to_similarity(distance: float) -> float:
    """
    Convert a FAISS L2 (Euclidean) distance between two L2-normalized
    vectors into a cosine-similarity-like score in [0, 1].

    For unit vectors: ||a - b||^2 = 2 - 2*cos(a,b)  =>  cos(a,b) = 1 - d^2/2
    We clamp to [0, 1] to keep the displayed score intuitive even with
    minor floating point drift.
    """
    similarity = 1 - (distance**2) / 2
    return max(0.0, min(1.0, similarity))


def search_query(
    vectorstore: FAISS,
    query: str,
    top_k: int = DEFAULT_TOP_K,
    score_threshold: Optional[float] = None,
) -> List[dict]:
    """
    Run a semantic similarity search and return the Top-K most relevant
    chunks as a list of plain dicts, ready for display or further
    processing (e.g. passing to an LLM in a RAG pipeline).

    Args:
        vectorstore: a loaded FAISS vectorstore (see load_faiss_index()).
        query: the user's natural-language search query.
        top_k: number of results to return.
        score_threshold: optional minimum similarity (0-1) a result must
            have to be included. Results below this are dropped. If this
            causes ALL results to be dropped, an empty list is returned
            (caller should display "No relevant information found.").

    Returns:
        List of dicts: {rank, source, page, chunk_id, score, content}
        Empty list if nothing relevant was found.

    Raises:
        ValueError: if the query is empty/invalid (see utils.validate_query).
    """
    query = validate_query(query)

    if vectorstore.index.ntotal == 0:
        logger.warning("The FAISS index is empty (0 vectors).")
        return []

    # similarity_search_with_score returns (Document, l2_distance) tuples,
    # sorted from most to least similar (smallest distance first).
    raw_results = vectorstore.similarity_search_with_score(query, k=top_k)

    results = []
    for rank, (doc, distance) in enumerate(raw_results, start=1):
        score = _l2_distance_to_similarity(distance)
        if score_threshold is not None and score < score_threshold:
            continue
        results.append(
            {
                "rank": rank,
                "source": doc.metadata.get("source", "unknown"),
                "page": doc.metadata.get("page"),
                "chunk_id": doc.metadata.get("chunk_id", "n/a"),
                "score": score,
                "content": doc.page_content.strip(),
            }
        )

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Run a one-off semantic search against the saved FAISS index")
    parser.add_argument("--query", required=True, help="Natural language search query")
    parser.add_argument(
        "--top-k", type=int, default=DEFAULT_TOP_K, help="Number of results to return")
    parser.add_argument(
        "--index-dir", default="faiss_index",
        help="Folder containing the saved FAISS index")
    parser.add_argument(
        "--threshold", type=float, default=None,
        help="Optional minimum similarity score (0-1)")
    parser.add_argument(
        "--force-fallback", action="store_true",
        help="Force offline TF-IDF+SVD embeddings")
    args = parser.parse_args()

    setup_logging()
    try:
        embedding_model = get_embedding_model(
            index_dir=args.index_dir, force_fallback=args.force_fallback)
        vectorstore = load_faiss_index(args.index_dir, embedding_model)
        results = search_query(
            vectorstore, args.query, top_k=args.top_k, score_threshold=args.threshold)
        print_search_results(args.query, results)
    except (FileNotFoundError, ValueError) as exc:
        logger.error(str(exc))
        sys.exit(1)


if __name__ == "__main__":
    main()