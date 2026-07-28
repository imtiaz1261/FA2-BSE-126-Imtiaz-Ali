"""src/report_generator.py — Turns per-method evaluation metrics into a
CSV export, comparison charts, and a markdown performance report.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # non-interactive backend — this script only saves files, never shows a window
import matplotlib.pyplot as plt
import pandas as pd


def build_comparison_dataframe(results_by_method: dict[str, dict[str, float]]) -> pd.DataFrame:
    """Converts {method_name: {metric_name: value}} into a tidy DataFrame
    with one row per method, for CSV export and charting."""
    df = pd.DataFrame.from_dict(results_by_method, orient="index")
    df.index.name = "method"
    return df.reset_index()


def export_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def plot_metric_comparison(df: pd.DataFrame, metric_columns: list[str], output_path: Path) -> None:
    """Draws a grouped bar chart comparing every method across every
    metric, and saves it as a PNG."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(10, 6))
    x = range(len(df))
    bar_width = 0.8 / len(metric_columns)

    for i, metric in enumerate(metric_columns):
        offsets = [pos + i * bar_width for pos in x]
        ax.bar(offsets, df[metric], width=bar_width, label=metric)

    ax.set_xticks([pos + bar_width * (len(metric_columns) - 1) / 2 for pos in x])
    ax.set_xticklabels(df["method"], rotation=15, ha="right")
    ax.set_ylabel("Score")
    ax.set_title("Retrieval Method Comparison")
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def plot_latency_comparison(latency_by_method: dict[str, float], output_path: Path) -> None:
    """Draws a bar chart of retrieval latency per method."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(8, 5))
    methods = list(latency_by_method.keys())
    latencies = list(latency_by_method.values())

    ax.bar(methods, latencies, color="steelblue")
    ax.set_ylabel("Latency (seconds)")
    ax.set_title("Retrieval Latency by Method")
    plt.xticks(rotation=15, ha="right")
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def generate_markdown_report(
    df: pd.DataFrame,
    latency_by_method: dict[str, float],
    chart_path: Path,
    latency_chart_path: Path,
    output_path: Path,
) -> None:
    """Assembles the full markdown evaluation report required by Phase 5
    of the project spec."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    best_method = df.loc[df["ndcg_at_k"].idxmax(), "method"]

    lines = [
        "# Hybrid RAG System — Evaluation Report",
        "",
        "## Project Overview",
        "",
        "This report evaluates four retrieval configurations on the same "
        "corpus and query set: BM25 alone, vector search alone, hybrid "
        "fusion of both, and hybrid fusion followed by cross-encoder "
        "reranking.",
        "",
        "## System Architecture",
        "",
        "```",
        "Query",
        "  |-- BM25 retrieval (sparse, keyword-based)",
        "  |-- Vector retrieval (dense, embedding-based)",
        "        |",
        "        v",
        "  Hybrid fusion (weighted score normalization + merge + dedup)",
        "        |",
        "        v",
        "  Cross-Encoder reranking (joint query-document scoring)",
        "        |",
        "        v",
        "  LLM answer generation (grounded in reranked context)",
        "```",
        "",
        "## Hybrid Retrieval Workflow",
        "",
        "BM25 and vector search each independently retrieve their own "
        "top-K candidates. Scores from both are min-max normalized to a "
        "0-1 range (since BM25 and cosine/L2-based similarity scores "
        "live on incompatible scales), then combined via a configurable "
        "weighted sum. Documents found by both retrievers naturally rank "
        "higher than documents found by only one.",
        "",
        "## Reranking Methodology",
        "",
        "The cross-encoder model scores each (query, document) pair "
        "jointly, rather than comparing independently-computed "
        "embeddings. This lets it capture fine-grained interactions "
        "between query and document text that bi-encoder approaches "
        "(BM25, vector search) cannot, at the cost of being too slow to "
        "run against an entire corpus — hence its use only on an "
        "already-narrowed shortlist.",
        "",
        "## Experimental Setup",
        "",
        "- Corpus size: 12 documents across 4 topics",
        "- Evaluation queries: 8 queries with hand-labeled ground-truth relevance",
        "- K (for Precision@K, Recall@K, NDCG@K): as configured in `config.py`",
        "",
        "## Performance Metrics",
        "",
        df.to_markdown(index=False),
        "",
        "## Before vs. After Reranking Comparison",
        "",
        "Comparing `hybrid` against `hybrid_reranked` isolates the exact "
        "effect of adding cross-encoder reranking on top of hybrid "
        "retrieval, holding the candidate set otherwise constant.",
        "",
        f"![Metric comparison]({chart_path.name})",
        "",
        "## Retrieval Latency Analysis",
        "",
        f"![Latency comparison]({latency_chart_path.name})",
        "",
        "Reranking adds measurable latency (an extra model inference per "
        "candidate document) but operates only on the small post-fusion "
        "shortlist, not the full corpus, keeping the added cost bounded "
        "regardless of total corpus size.",
        "",
        "## Strengths, Limitations, and Future Improvements",
        "",
        f"**Best-performing method by NDCG@K: `{best_method}`**",
        "",
        "**Strengths:** Hybrid retrieval captures both exact keyword "
        "matches and semantic similarity; reranking further improves "
        "precision on the final shortlist.",
        "",
        "**Limitations:** Evaluated on a small, synthetic corpus (12 "
        "documents); cross-encoder reranking adds latency that may "
        "matter at scale.",
        "",
        "**Future improvements:** query expansion, metadata filtering, "
        "adjustable fusion weights per query type, larger-scale "
        "evaluation corpus.",
    ]

    output_path.write_text("\n".join(lines), encoding="utf-8")
