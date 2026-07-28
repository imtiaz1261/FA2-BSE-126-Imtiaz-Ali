"""
state.py
--------
The shared state schema that flows through every node of the LangGraph
graph. LangGraph merges partial dict updates returned by each node into
this state, so every field here is something a node can read and/or
update.
"""

from typing import Dict, List, Optional, TypedDict


class SourceResult(TypedDict):
    title: str
    url: str
    snippet: str


class ResearchState(TypedDict, total=False):
    # --- Input ---
    query: str

    # --- Phase 1: Planning ---
    objective: str
    tasks: List[str]
    current_task_index: int

    # --- Phase 2: Web research ---
    search_results: Dict[str, List[SourceResult]]   # task -> deduplicated sources

    # --- Phase 3: Validation / retry ---
    validated: Dict[str, bool]
    retry_counts: Dict[str, int]
    route_decision: str    # "retry" | "continue" | "done" -- set by validator, read by the router

    # --- Phase 4: Summarization ---
    task_summaries: Dict[str, str]
    combined_summary: str

    # --- Phase 5: Report generation ---
    report_markdown: str
    report_title: str

    # --- Cross-cutting: logging / error recovery ---
    node_log: List[str]      # human-readable execution history, in order
    errors: List[str]        # non-fatal errors encountered along the way


def new_initial_state(query: str) -> ResearchState:
    """Build a fresh state dict for a new research run."""
    return ResearchState(
        query=query,
        objective="",
        tasks=[],
        current_task_index=0,
        search_results={},
        validated={},
        retry_counts={},
        route_decision="",
        task_summaries={},
        combined_summary="",
        report_markdown="",
        report_title="",
        node_log=[],
        errors=[],
    )
