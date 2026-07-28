"""scripts/run_query.py — Runs one query through the full pipeline:
hybrid retrieval -> cross-encoder reranking -> LLM answer generation,
displaying every intermediate stage.

    python scripts/run_query.py --query "What causes global warming?"
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv  # noqa: E402
from openai import OpenAI  # noqa: E402

import config  # noqa: E402
from src.bm25_retriever import BM25Retriever  # noqa: E402
from src.vector_retriever import VectorRetriever  # noqa: E402
from src.hybrid_retriever import hybrid_fuse  # noqa: E402
from src.reranker import Reranker  # noqa: E402
from src.rag_chain import generate_answer  # noqa: E402


def load_api_key() -> str:
    load_dotenv()
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key or "your_api_key_here" in api_key:
        raise EnvironmentError(
            "GROQ_API_KEY missing. Create a .env file with:\n"
            "  GROQ_API_KEY=your_actual_key_here\n"
            "Get a free key at https://console.groq.com/keys"
        )
    return api_key


def run_pipeline(query: str, api_key: str) -> None:
    print(f"\nQuery: {query}\n{'=' * 70}")

    bm25 = BM25Retriever.load(config.BM25_INDEX_PATH)
    vector = VectorRetriever(config.EMBEDDING_MODEL_NAME)
    vector.load(config.FAISS_INDEX_PATH)

    bm25_results = bm25.search(query, top_k=config.TOP_K_BM25)
    vector_results = vector.search(query, top_k=config.TOP_K_VECTOR)

    print("\n--- BM25 results ---")
    for r in bm25_results:
        print(f"  {r.doc_id}  (score={r.score:.3f})")

    print("\n--- Vector search results ---")
    for r in vector_results:
        print(f"  {r.doc_id}  (score={r.score:.3f})")

    hybrid_results = hybrid_fuse(
        bm25_results, vector_results,
        bm25_weight=config.BM25_WEIGHT, vector_weight=config.VECTOR_WEIGHT,
        top_k=config.TOP_K_HYBRID,
    )
    print("\n--- Hybrid fused results ---")
    for r in hybrid_results:
        print(f"  {r.doc_id}  (score={r.score:.3f})")

    reranker = Reranker(config.CROSS_ENCODER_MODEL_NAME)
    reranked_results = reranker.rerank(query, hybrid_results, top_k=config.TOP_K_RERANKED)
    print("\n--- Reranked results (final context for LLM) ---")
    for r in reranked_results:
        print(f"  {r.doc_id}  (score={r.score:.3f})")

    client = OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")
    answer = generate_answer(client, config.LLM_MODEL_NAME, query, reranked_results)

    print(f"\n--- Final Answer ---\n{answer}")
    print("=" * 70)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a query through the hybrid RAG pipeline")
    parser.add_argument("--query", required=True, help="The question to ask")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    api_key = load_api_key()
    run_pipeline(args.query, api_key)


if __name__ == "__main__":
    main()
