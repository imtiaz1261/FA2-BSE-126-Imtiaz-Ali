"""scripts/evaluate.py — Runs all four retrieval configurations (BM25
only, vector only, hybrid, hybrid+reranked) against every query in
eval_queries.json, computes Precision@K/Recall@K/MRR/NDCG@K for each,
measures latency, and generates the full evaluation report (CSV +
charts + markdown).

    python scripts/evaluate.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import config  # noqa: E402
from src.bm25_retriever import BM25Retriever  # noqa: E402
from src.vector_retriever import VectorRetriever  # noqa: E402
from src.hybrid_retriever import hybrid_fuse  # noqa: E402
from src.reranker import Reranker  # noqa: E402
from src.metrics import evaluate_single_query, average_metrics  # noqa: E402
from src.report_generator import (  # noqa: E402
    build_comparison_dataframe,
    export_csv,
    plot_metric_comparison,
    plot_latency_comparison,
    generate_markdown_report,
)


def load_eval_queries(path: Path) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(f"Evaluation queries not found at: {path}")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def evaluate_method(
    method_name: str,
    retrieve_fn,
    eval_queries: list[dict],
    k: int,
) -> tuple[dict[str, float], float]:
    """Runs one retrieval method against every eval query, returning its
    averaged metrics and average per-query latency.

    `retrieve_fn` is a callable: (query: str) -> list[doc_id strings]
    """
    per_query_metrics = []
    latencies = []

    for item in eval_queries:
        query = item["query"]
        relevant_ids = set(item["relevant_doc_ids"])

        start = time.perf_counter()
        retrieved_ids = retrieve_fn(query)
        elapsed = time.perf_counter() - start
        latencies.append(elapsed)

        metrics = evaluate_single_query(retrieved_ids, relevant_ids, k)
        per_query_metrics.append(metrics)

    avg_metrics = average_metrics(per_query_metrics)
    avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
    return avg_metrics, avg_latency


def main() -> None:
    print("Loading indexes and evaluation queries...")
    bm25 = BM25Retriever.load(config.BM25_INDEX_PATH)
    vector = VectorRetriever(config.EMBEDDING_MODEL_NAME)
    vector.load(config.FAISS_INDEX_PATH)
    reranker = Reranker(config.CROSS_ENCODER_MODEL_NAME)
    eval_queries = load_eval_queries(config.EVAL_QUERIES_PATH)
    print(f"Loaded {len(eval_queries)} evaluation queries.\n")

    results_by_method: dict[str, dict[str, float]] = {}
    latency_by_method: dict[str, float] = {}

    def bm25_only(query: str) -> list[str]:
        results = bm25.search(query, top_k=config.TOP_K_BM25)
        return [r.doc_id for r in results]

    metrics, latency = evaluate_method("bm25_only", bm25_only, eval_queries, config.EVAL_K)
    results_by_method["bm25_only"] = metrics
    latency_by_method["bm25_only"] = latency
    print(f"bm25_only:        {metrics}  (avg latency: {latency:.4f}s)")

    def vector_only(query: str) -> list[str]:
        results = vector.search(query, top_k=config.TOP_K_VECTOR)
        return [r.doc_id for r in results]

    metrics, latency = evaluate_method("vector_only", vector_only, eval_queries, config.EVAL_K)
    results_by_method["vector_only"] = metrics
    latency_by_method["vector_only"] = latency
    print(f"vector_only:      {metrics}  (avg latency: {latency:.4f}s)")

    def hybrid_only(query: str) -> list[str]:
        bm25_results = bm25.search(query, top_k=config.TOP_K_BM25)
        vector_results = vector.search(query, top_k=config.TOP_K_VECTOR)
        fused = hybrid_fuse(
            bm25_results, vector_results,
            bm25_weight=config.BM25_WEIGHT, vector_weight=config.VECTOR_WEIGHT,
            top_k=config.TOP_K_HYBRID,
        )
        return [r.doc_id for r in fused]

    metrics, latency = evaluate_method("hybrid", hybrid_only, eval_queries, config.EVAL_K)
    results_by_method["hybrid"] = metrics
    latency_by_method["hybrid"] = latency
    print(f"hybrid:           {metrics}  (avg latency: {latency:.4f}s)")

    def hybrid_reranked(query: str) -> list[str]:
        bm25_results = bm25.search(query, top_k=config.TOP_K_BM25)
        vector_results = vector.search(query, top_k=config.TOP_K_VECTOR)
        fused = hybrid_fuse(
            bm25_results, vector_results,
            bm25_weight=config.BM25_WEIGHT, vector_weight=config.VECTOR_WEIGHT,
            top_k=config.TOP_K_HYBRID,
        )
        reranked = reranker.rerank(query, fused, top_k=config.TOP_K_RERANKED)
        return [r.doc_id for r in reranked]

    metrics, latency = evaluate_method("hybrid_reranked", hybrid_reranked, eval_queries, config.EVAL_K)
    results_by_method["hybrid_reranked"] = metrics
    latency_by_method["hybrid_reranked"] = latency
    print(f"hybrid_reranked:  {metrics}  (avg latency: {latency:.4f}s)")

    print("\nGenerating report...")
    df = build_comparison_dataframe(results_by_method)

    csv_path = config.REPORTS_DIR / "evaluation_results.csv"
    chart_path = config.REPORTS_DIR / "metrics_comparison.png"
    latency_chart_path = config.REPORTS_DIR / "latency_comparison.png"
    report_path = config.REPORTS_DIR / "evaluation_report.md"

    export_csv(df, csv_path)
    plot_metric_comparison(df, ["precision_at_k", "recall_at_k", "mrr", "ndcg_at_k"], chart_path)
    plot_latency_comparison(latency_by_method, latency_chart_path)
    generate_markdown_report(df, latency_by_method, chart_path, latency_chart_path, report_path)

    print(f"\nCSV:    {csv_path}")
    print(f"Chart:  {chart_path}")
    print(f"Chart:  {latency_chart_path}")
    print(f"Report: {report_path}")
    print("\nEvaluation complete.")


if __name__ == "__main__":
    main()
