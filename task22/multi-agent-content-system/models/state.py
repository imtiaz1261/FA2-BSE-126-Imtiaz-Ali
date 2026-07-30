"""models/state.py — The shared state object that flows through the
LangGraph workflow.

LangGraph expects state as a TypedDict (not a Pydantic BaseModel) at the
graph level — each node function receives the current state, returns a
partial update, and LangGraph merges it in. The individual VALUES inside
this TypedDict are still full Pydantic models (ContentRequest,
ResearchSummary, etc.), so we get validation on the meaningful data while
satisfying LangGraph's expected state container shape.
"""

from __future__ import annotations

from typing import TypedDict

from models.schemas import ContentRequest, Draft, FinalContent, ResearchSummary


class GraphState(TypedDict):
    """The complete state passed between every agent node.

    Fields start as None/empty and get filled in as each agent runs:
    request is always present from the start; research_summary is filled
    by the Researcher node; draft by the Writer node; final_content by
    the Editor node.
    """

    request: ContentRequest
    research_summary: ResearchSummary | None
    draft: Draft | None
    final_content: FinalContent | None
    current_stage: str
    errors: list[str]


def create_initial_state(request: ContentRequest) -> GraphState:
    """Builds the starting state for a new pipeline run, given a
    validated ContentRequest.

    Centralizing this construction (rather than building the dict
    ad-hoc wherever a run starts) guarantees every run begins with the
    exact same, correctly-shaped empty state.
    """
    return GraphState(
        request=request,
        research_summary=None,
        draft=None,
        final_content=None,
        current_stage="pending",
        errors=[],
    )
