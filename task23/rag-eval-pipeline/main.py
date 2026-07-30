"""
Main entry point: runs the full RAG evaluation pipeline end-to-end.

    1. Load evaluation dataset
    2. Query the RAG chatbot (retrieve + generate) for every question
    3. Compute evaluation metrics (RAGAS or offline heuristic fallback)
    4. Aggregate scores
    5. Generate visualizations
    6. Generate reports (CSV, JSON, Markdown, PDF)

Usage:
    python main.py                     # uses offline heuristic backend (no API key needed)
    python main.py --backend openai    # uses real RAGAS + OpenAI (requires OPENAI_API_KEY)
"""

from __future__ import annotations

import argparse
import sys

from dataset.loader import load_dataset
from evaluator.ragas_evaluator import RagasEvaluator
from metrics.aggregator import MetricsAggregator
from rag_pipeline.chatbot import RAGChatbot
from reports.report_generator import ReportGenerator
from utils.logger import get_logger
from visualizations.charts import plot_category_breakdown, plot_metric_averages

logger = get_logger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="RAG Chatbot Evaluation Pipeline (RAGAS)")
    parser.add_argument(
        "--backend",
        choices=["offline", "openai", "groq"],
        default="offline",
        help="'offline' runs a dependency-free demo (TF-IDF retrieval + heuristic metrics, "
        "no API key needed). 'openai' runs the production path (FAISS + OpenAI embeddings, "
        "an OpenAI chat model, and real RAGAS scoring) — requires OPENAI_API_KEY. 'groq' runs "
        "the same real RAGAS scoring but with Groq's free-tier LLM for generation/judging and "
        "local sentence-transformers embeddings for retrieval — requires GROQ_API_KEY.",
    )
    parser.add_argument(
        "--dataset",
        default="dataset/evaluation_dataset.json",
        help="Path to the evaluation dataset JSON file.",
    )
    parser.add_argument(
        "--output-dir",
        default="reports/output",
        help="Directory to write reports and charts to.",
    )
    parser.add_argument(
        "--k", type=int, default=3, help="Number of context chunks to retrieve per question."
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    logger.info("=== RAG Evaluation Pipeline starting (backend=%s) ===", args.backend)

    # 1. Load dataset
    dataset = load_dataset(args.dataset)

    # 2. Build chatbot + run evaluation
    chatbot_backend = "extractive" if args.backend == "offline" else args.backend
    chatbot = RAGChatbot(backend=chatbot_backend)

    evaluator = RagasEvaluator(chatbot, use_ragas=(args.backend != "offline"), k=args.k)
    results_df = evaluator.run(dataset)

    # 3. Aggregate
    aggregator = MetricsAggregator(results_df)
    overall = aggregator.overall_score()
    averages = aggregator.metric_averages()
    logger.info("Overall score: %.2f%%", overall * 100)
    for metric, score in averages.items():
        logger.info("  %-20s %.2f%%", metric, score * 100)

    # 4. Visualizations
    chart_paths = {
        "metric_averages": plot_metric_averages(averages, args.output_dir),
        "category_breakdown": plot_category_breakdown(
            aggregator.category_breakdown(), args.output_dir
        ),
    }

    # 5. Reports
    report_gen = ReportGenerator(results_df, args.output_dir)
    report_gen.export_csv()
    report_gen.export_json()
    report_gen.export_markdown(chart_paths)
    try:
        report_gen.export_pdf(chart_paths)
    except ImportError:
        logger.warning("reportlab not installed — skipping PDF export.")

    logger.info("=== Pipeline complete. Reports written to %s ===", args.output_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
