"""
main.py
-------
CLI entry point: run a single research query end-to-end through the
LangGraph workflow, print the execution log, and save the report.

Usage:
    python main.py "What are the latest advances in solid-state batteries?"
    python main.py "..." --format pdf
    python main.py "..." --format docx
    python main.py "..." --mermaid       # print the graph's Mermaid diagram
"""

import argparse
import sys
import uuid
from pathlib import Path

from config import OUTPUTS_DIR
from graph.build import build_graph, get_mermaid_diagram
from llm import LLMInitError
from state import new_initial_state
from utils import get_logger

logger = get_logger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Multi-Step Research Assistant")
    parser.add_argument("query", nargs="?", help="The research question to investigate.")
    parser.add_argument(
        "--format", choices=["markdown", "pdf", "docx"], default="markdown",
        help="Report export format (default: markdown).",
    )
    parser.add_argument("--mermaid", action="store_true", help="Print the graph's Mermaid diagram and exit.")
    return parser.parse_args()


def run_research(query: str) -> dict:
    """Run the full workflow for one query. Returns the final state dict."""
    graph = build_graph()
    thread_id = str(uuid.uuid4())[:8]
    config = {"configurable": {"thread_id": thread_id}}

    initial_state = new_initial_state(query)
    final_state = graph.invoke(initial_state, config=config)
    return final_state


def save_report(state: dict, fmt: str) -> Path:
    from report.report_builder import export_pdf, export_docx

    safe_name = "".join(c if c.isalnum() or c in " -_" else "" for c in state["query"])[:60].strip() or "report"
    if fmt == "markdown":
        path = OUTPUTS_DIR / f"{safe_name}.md"
        path.write_text(state["report_markdown"], encoding="utf-8")
    elif fmt == "pdf":
        path = export_pdf(state["report_title"], state["report_markdown"], OUTPUTS_DIR / f"{safe_name}.pdf")
    elif fmt == "docx":
        path = export_docx(state["report_title"], state["report_markdown"], OUTPUTS_DIR / f"{safe_name}.docx")
    else:
        raise ValueError(f"Unknown format: {fmt}")
    return path


def main() -> int:
    args = parse_args()

    if args.mermaid:
        try:
            print(get_mermaid_diagram())
        except LLMInitError as exc:
            print(f"Error: {exc}")
            return 1
        return 0

    if not args.query:
        print("Usage: python main.py \"your research question\" [--format markdown|pdf|docx]")
        return 1

    try:
        print(f"\nResearching: {args.query}\n")
        state = run_research(args.query)
    except LLMInitError as exc:
        print(f"\nError: {exc}")
        return 1
    except Exception as exc:
        logger.error("Research run failed: %s", exc)
        print(f"\nUnexpected error: {exc}")
        return 1

    print("=== Execution log ===")
    for entry in state.get("node_log", []):
        print(entry)

    if state.get("errors"):
        print("\n=== Non-fatal errors encountered ===")
        for err in state["errors"]:
            print(f"- {err}")

    print("\n=== Final report ===\n")
    print(state.get("report_markdown", "(no report generated)"))

    saved_path = save_report(state, args.format)
    print(f"\nReport saved to: {saved_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
