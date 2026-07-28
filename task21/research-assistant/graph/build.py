"""
graph/build.py
---------------
Assembles the LangGraph StateGraph:

    START -> planner -> web_search -> validator --(retry)--> web_search
                                          |--(continue: more tasks)--> web_search
                                          |--(done: all tasks handled)--> summarizer
                                                                              |
                                                                              v
                                                                     report_generator -> END

- Conditional edges: route_after_validation() (graph/nodes.py) decides
  retry vs. continue vs. done after every validator run.
- Retry logic: validator_node increments a per-task retry counter and
  loops back to web_search until MAX_RETRIES_PER_TASK is hit.
- Error handling/recovery: every node is wrapped with `_safe_node`,
  which catches unexpected exceptions, records them in state["errors"],
  and returns a safe, non-crashing update instead of failing the whole
  run -- so one bad node doesn't take down the entire workflow.
- Checkpointing: the compiled graph uses an in-memory checkpointer
  (MemorySaver) keyed by thread_id, so a given run's state can be
  inspected or resumed via the same thread_id.
"""

from functools import wraps

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from graph.nodes import (
    planner_node,
    web_search_node,
    validator_node,
    route_after_validation,
    summarizer_node,
    report_generator_node,
)
from state import ResearchState
from utils import get_logger

logger = get_logger(__name__)


def _safe_node(node_fn, safe_route_decision: str = "done"):
    """Wrap a node function so an unexpected exception doesn't crash the
    whole graph run -- it's recorded as an error and the workflow can
    still proceed (or terminate gracefully) instead of raising."""

    @wraps(node_fn)
    def wrapped(state: ResearchState) -> dict:
        try:
            return node_fn(state)
        except Exception as exc:
            logger.error("Node '%s' raised an unexpected error: %s", node_fn.__name__, exc)
            errors = list(state.get("errors", []))
            errors.append(f"{node_fn.__name__} failed unexpectedly: {exc}")
            node_log = list(state.get("node_log", []))
            node_log.append(f"[ERROR] {node_fn.__name__}: {exc}")
            # Ensure the router always has a safe decision to avoid infinite loops
            update = {"errors": errors, "node_log": node_log}
            if node_fn is validator_node:
                update["route_decision"] = safe_route_decision
            return update

    return wrapped


def build_graph():
    """Compile and return the research assistant's LangGraph graph."""
    graph = StateGraph(ResearchState)

    graph.add_node("planner", _safe_node(planner_node))
    graph.add_node("web_search", _safe_node(web_search_node))
    graph.add_node("validator", _safe_node(validator_node))
    graph.add_node("summarizer", _safe_node(summarizer_node))
    graph.add_node("report_generator", _safe_node(report_generator_node))

    graph.set_entry_point("planner")
    graph.add_edge("planner", "web_search")
    graph.add_edge("web_search", "validator")

    graph.add_conditional_edges(
        "validator",
        route_after_validation,
        {
            "web_search": "web_search",   # covers both "retry" and "continue"
            "summarizer": "summarizer",
        },
    )

    graph.add_edge("summarizer", "report_generator")
    graph.add_edge("report_generator", END)

    checkpointer = MemorySaver()
    compiled = graph.compile(checkpointer=checkpointer)
    logger.info("Research assistant graph compiled with checkpointing enabled.")
    return compiled


def get_mermaid_diagram() -> str:
    """Return the graph's structure as Mermaid syntax, for visualization
    (paste into https://mermaid.live or a Markdown renderer that supports it)."""
    graph = build_graph()
    return graph.get_graph().draw_mermaid()
