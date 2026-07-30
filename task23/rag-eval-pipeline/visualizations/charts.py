"""
Chart generation for the evaluation report.

All functions save a PNG to `output_dir` and return the file path, so the
report generator can embed them by reference (Markdown/PDF) without holding
image bytes in memory.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless rendering — no display needed
import matplotlib.pyplot as plt
import pandas as pd

from utils.logger import get_logger

logger = get_logger(__name__)

_COLOR = "#4C72B0"


def plot_metric_averages(
    metric_averages: dict[str, float], output_dir: str | Path
) -> Path:
    """Bar chart: average score per metric."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(8, 5))
    metrics = list(metric_averages.keys())
    values = list(metric_averages.values())

    bars = ax.bar(metrics, values, color=_COLOR)
    ax.set_ylim(0, 1.0)
    ax.set_ylabel("Average score")
    ax.set_title("Average Score by Metric")
    ax.set_xticks(range(len(metrics)))
    ax.set_xticklabels(metrics, rotation=30, ha="right")

    for bar, value in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.02,
            f"{value:.2f}",
            ha="center",
            fontsize=9,
        )

    fig.tight_layout()
    path = output_dir / "metric_averages.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    logger.info("Saved chart: %s", path)
    return path


def plot_category_breakdown(
    category_breakdown: pd.DataFrame, output_dir: str | Path
) -> Path:
    """Grouped bar chart: average score per metric, broken down by question category."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(10, 6))
    category_breakdown.plot(kind="bar", ax=ax)
    ax.set_ylim(0, 1.0)
    ax.set_ylabel("Average score")
    ax.set_title("Metric Scores by Question Category")
    ax.legend(loc="upper right", fontsize=8)
    ax.set_xticks(range(len(category_breakdown.index)))
    ax.set_xticklabels(category_breakdown.index, rotation=30, ha="right")

    fig.tight_layout()
    path = output_dir / "category_breakdown.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    logger.info("Saved chart: %s", path)
    return path


def plot_per_question_scores(
    results_df: pd.DataFrame, metric: str, output_dir: str | Path
) -> Path:
    """Line/scatter chart of a single metric's score across every question, in
    dataset order — useful for spotting clusters of weak questions."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(results_df["id"], results_df[metric], marker="o", color=_COLOR)
    ax.axhline(results_df[metric].mean(), color="gray", linestyle="--", linewidth=1)
    ax.set_ylim(0, 1.05)
    ax.set_ylabel(metric.replace("_", " ").title())
    ax.set_title(f"{metric.replace('_', ' ').title()} — Per Question")
    ax.set_xticks(range(len(results_df["id"])))
    ax.set_xticklabels(results_df["id"], rotation=45, ha="right")

    fig.tight_layout()
    path = output_dir / f"per_question_{metric}.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    logger.info("Saved chart: %s", path)
    return path
