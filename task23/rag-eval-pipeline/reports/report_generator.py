"""
Report generation: turns evaluation results + aggregated stats into
CSV, JSON, Markdown, and PDF deliverables.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from metrics.aggregator import MetricsAggregator
from utils.logger import get_logger

logger = get_logger(__name__)


class ReportGenerator:
    def __init__(self, results_df: pd.DataFrame, output_dir: str | Path):
        self.results_df = results_df
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.aggregator = MetricsAggregator(results_df)

    # ------------------------------------------------------------------ #
    # Data exports
    # ------------------------------------------------------------------ #
    def export_csv(self) -> Path:
        path = self.output_dir / "evaluation_results.csv"
        self.results_df.to_csv(path, index=False)
        logger.info("Exported CSV report: %s", path)
        return path

    def export_json(self) -> Path:
        path = self.output_dir / "evaluation_results.json"
        payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "overall_score": self.aggregator.overall_score(),
            "metric_averages": self.aggregator.metric_averages(),
            "category_breakdown": self.aggregator.category_breakdown().to_dict(orient="index"),
            "per_question_results": self.results_df.to_dict(orient="records"),
        }
        with path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        logger.info("Exported JSON report: %s", path)
        return path

    # ------------------------------------------------------------------ #
    # Markdown report
    # ------------------------------------------------------------------ #
    def export_markdown(self, chart_paths: dict[str, Path] | None = None) -> Path:
        chart_paths = chart_paths or {}
        averages = self.aggregator.metric_averages()
        overall = self.aggregator.overall_score()
        weakest_metric, weakest_score = self.aggregator.weakest_metric()
        strongest_metric, strongest_score = self.aggregator.strongest_metric()
        category_breakdown = self.aggregator.category_breakdown()
        lowest_questions = self.aggregator.lowest_scoring_questions(weakest_metric, n=3)

        lines: list[str] = []
        lines.append("# RAG Chatbot Evaluation Report")
        lines.append(f"\n_Generated: {datetime.now(timezone.utc).isoformat()}_\n")

        lines.append("## Overall Evaluation Summary")
        lines.append(f"\n**Overall Score: {overall:.2%}**\n")
        lines.append(f"- Strongest metric: **{strongest_metric}** ({strongest_score:.2%})")
        lines.append(f"- Weakest metric: **{weakest_metric}** ({weakest_score:.2%})")
        lines.append(f"- Total questions evaluated: {len(self.results_df)}\n")

        lines.append("## Metric-wise Performance")
        lines.append("\n| Metric | Average Score |")
        lines.append("|---|---|")
        for metric, score in averages.items():
            lines.append(f"| {metric.replace('_', ' ').title()} | {score:.2%} |")

        if "metric_averages" in chart_paths:
            lines.append(f"\n![Metric Averages]({chart_paths['metric_averages'].name})")

        lines.append("\n## Performance by Question Category")
        lines.append(f"\n{category_breakdown.to_markdown()}\n")

        if "category_breakdown" in chart_paths:
            lines.append(f"\n![Category Breakdown]({chart_paths['category_breakdown'].name})")

        lines.append("\n## Per-Question Results")
        display_cols = ["id", "category", "question"] + list(averages.keys())
        lines.append(f"\n{self.results_df[display_cols].to_markdown(index=False)}\n")

        lines.append(f"\n## {weakest_metric.replace('_', ' ').title()} Analysis")
        lines.append(
            f"\n**{weakest_metric.replace('_', ' ').title()}** is the weakest metric "
            f"at {weakest_score:.2%}. The lowest-scoring questions on this metric:\n"
        )
        lines.append(f"\n{lowest_questions.to_markdown(index=False)}\n")

        lines.append("\n## Strengths and Weaknesses")
        lines.append(f"\n**Strengths:** {strongest_metric.replace('_', ' ').title()} performs "
                      f"best, suggesting the pipeline is comparatively reliable in that dimension.\n")
        lines.append(f"\n**Weaknesses:** {weakest_metric.replace('_', ' ').title()} lags behind, "
                      f"concentrated in the categories shown above.\n")

        lines.append("\n## Improvement Recommendations")
        lines.extend(self._recommendations(averages))

        content = "\n".join(lines)
        path = self.output_dir / "evaluation_report.md"
        path.write_text(content, encoding="utf-8")
        logger.info("Exported Markdown report: %s", path)
        return path

    def _recommendations(self, averages: dict[str, float]) -> list[str]:
        recs = []
        if averages.get("faithfulness", 1) < 0.6:
            recs.append(
                "- Faithfulness is low: tighten the generation prompt to explicitly forbid "
                "adding information not present in retrieved context, and consider a "
                "post-hoc groundedness check."
            )
        if averages.get("context_precision", 1) < 0.6:
            recs.append(
                "- Context precision is low: review chunking strategy and retriever "
                "top-k value; irrelevant chunks are likely diluting the context window."
            )
        if averages.get("context_recall", 1) < 0.6:
            recs.append(
                "- Context recall is low: the retriever may be missing relevant documents "
                "entirely — consider hybrid search (keyword + embedding) or increasing k."
            )
        if averages.get("answer_relevancy", 1) < 0.6:
            recs.append(
                "- Answer relevancy is low: answers may be drifting from the question — "
                "consider re-ranking retrieved context before generation."
            )
        if not recs:
            recs.append(
                "- All metrics are performing reasonably well; focus on expanding the "
                "evaluation dataset to catch edge cases not yet covered."
            )
        return recs

    # ------------------------------------------------------------------ #
    # PDF report (bonus)
    # ------------------------------------------------------------------ #
    def export_pdf(self, chart_paths: dict[str, Path] | None = None) -> Path:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import (
            Image,
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )

        chart_paths = chart_paths or {}
        styles = getSampleStyleSheet()
        path = self.output_dir / "evaluation_report.pdf"
        doc = SimpleDocTemplate(str(path), pagesize=letter)
        story = []

        overall = self.aggregator.overall_score()
        averages = self.aggregator.metric_averages()

        story.append(Paragraph("RAG Chatbot Evaluation Report", styles["Title"]))
        story.append(Spacer(1, 12))
        story.append(Paragraph(f"Overall Score: {overall:.2%}", styles["Heading2"]))
        story.append(Spacer(1, 12))

        table_data = [["Metric", "Average Score"]] + [
            [m.replace("_", " ").title(), f"{s:.2%}"] for m, s in averages.items()
        ]
        table = Table(table_data, hAlign="LEFT")
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4C72B0")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                ]
            )
        )
        story.append(table)
        story.append(Spacer(1, 20))

        for key in ("metric_averages", "category_breakdown"):
            if key in chart_paths and Path(chart_paths[key]).exists():
                story.append(Image(str(chart_paths[key]), width=420, height=260))
                story.append(Spacer(1, 16))

        doc.build(story)
        logger.info("Exported PDF report: %s", path)
        return path
