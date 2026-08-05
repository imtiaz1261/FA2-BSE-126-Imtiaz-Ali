"""
Agent executor service — Phase 11.

`run_agent` is the single entry-point for running the LangGraph agent.
It pre-populates the AgentState, invokes the compiled graph, and returns
a structured AgentResult with the final answer and full tool trace.

`stream_agent` is the streaming variant — it yields AgentEvent dicts
that map onto the wire protocol consumed by the frontend.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Dict, List, Optional

from sqlalchemy.orm import Session

from app.agents.graph import get_compiled_graph
from app.agents.state import AgentState
from app.core.config import settings
from app.models.message import Message

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass
class AgentResult:
    final_answer: str
    intent: Optional[str] = None
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    tool_results: List[Dict[str, Any]] = field(default_factory=list)
    iterations: int = 0
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# History → OpenAI messages conversion
# ---------------------------------------------------------------------------


def _history_to_messages(history: List[Message]) -> List[Dict[str, Any]]:
    """Convert persisted Message rows to OpenAI message dicts."""
    from app.models.message import MessageRole

    result = []
    for msg in history[-settings.LLM_MAX_HISTORY_MESSAGES :]:
        if msg.role == MessageRole.SYSTEM:
            continue
        result.append({"role": msg.role.value, "content": msg.content})
    return result


# ---------------------------------------------------------------------------
# run_agent — blocking (full graph traversal, returns when done)
# ---------------------------------------------------------------------------


async def run_agent(
    user_message: str,
    user_id: uuid.UUID,
    conversation_id: uuid.UUID,
    history: List[Message],
    db: Session,
) -> AgentResult:
    """
    Run the LangGraph agent to completion and return an AgentResult.

    Args:
        user_message:     The current user turn text.
        user_id:          Requesting user's UUID (for tool injection).
        conversation_id:  Conversation UUID (stored in state for context).
        history:          Persisted Message rows (excluding the new turn).
        db:               SQLAlchemy session (for document_search tool).

    Returns:
        AgentResult with final_answer, tool trace, and metadata.
    """
    graph = get_compiled_graph()

    # Build the initial message list from history + new user turn
    messages = _history_to_messages(history)
    messages.append({"role": "user", "content": user_message})

    initial_state: AgentState = {
        "user_id": user_id,
        "conversation_id": conversation_id,
        "messages": messages,
        "intent": None,
        "tool_calls": [],
        "tool_results": [],
        "iteration": 0,
        "max_iterations": settings.AGENT_MAX_ITERATIONS,
        "error": None,
        "final_answer": None,
        # db is NOT part of AgentState TypedDict but we pass it via inject;
        # The execute_tools node reads it from state["db"] if present.
        # We attach it as a side-channel key (LangGraph tolerates extra keys).
        "db": db,  # type: ignore[typeddict-item]
    }

    try:
        final_state: AgentState = await asyncio.wait_for(
            graph.ainvoke(initial_state),
            timeout=settings.AGENT_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        logger.error(
            "Agent run timed out after %ds for conversation %s",
            settings.AGENT_TIMEOUT_SECONDS,
            conversation_id,
        )
        return AgentResult(
            final_answer=(
                "I'm sorry, the agent timed out before completing. "
                "Please try again with a simpler request."
            ),
            error="timeout",
        )
    except Exception as exc:
        logger.exception("Agent run failed for conversation %s", conversation_id)
        return AgentResult(
            final_answer=f"Agent error: {exc}",
            error=str(exc),
        )

    return AgentResult(
        final_answer=final_state.get("final_answer") or "",
        intent=final_state.get("intent"),
        tool_calls=final_state.get("tool_results", []),   # results include call metadata
        tool_results=final_state.get("tool_results", []),
        iterations=final_state.get("iteration", 0),
        error=final_state.get("error"),
    )


# ---------------------------------------------------------------------------
# stream_agent — yields AgentEvent dicts as the graph progresses
# ---------------------------------------------------------------------------


async def stream_agent(
    user_message: str,
    user_id: uuid.UUID,
    conversation_id: uuid.UUID,
    history: List[Message],
    db: Session,
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Stream agent events as the graph runs, yielding dicts with keys:
        {"type": "intent",       "intent": "tools"|"direct"|"clarify"}
        {"type": "tool_call",    "name": str, "arguments": dict}
        {"type": "tool_result",  "name": str, "result": str}
        {"type": "token",        "content": str}
        {"type": "final",        "answer": str, "iterations": int}
        {"type": "error",        "message": str}
    """
    graph = get_compiled_graph()

    messages = _history_to_messages(history)
    messages.append({"role": "user", "content": user_message})

    initial_state: AgentState = {
        "user_id": user_id,
        "conversation_id": conversation_id,
        "messages": messages,
        "intent": None,
        "tool_calls": [],
        "tool_results": [],
        "iteration": 0,
        "max_iterations": settings.AGENT_MAX_ITERATIONS,
        "error": None,
        "final_answer": None,
        "db": db,  # type: ignore[typeddict-item]
    }

    try:
        async for event in graph.astream(initial_state, stream_mode="updates"):
            # event is a dict: {node_name: {state_updates}}
            for node_name, updates in event.items():
                if not isinstance(updates, dict):
                    continue

                # Intent classified
                if "intent" in updates:
                    yield {"type": "intent", "intent": updates["intent"]}

                # New tool calls issued by LLM
                if updates.get("tool_calls"):
                    for tc in updates["tool_calls"]:
                        try:
                            args = json_safe_loads(tc.get("arguments", "{}"))
                        except Exception:
                            args = {}
                        yield {
                            "type": "tool_call",
                            "name": tc["name"],
                            "arguments": args,
                        }

                # Tool results arrived
                if updates.get("tool_results"):
                    # Only yield newly added results (avoid re-emitting history)
                    for tr in updates["tool_results"]:
                        yield {
                            "type": "tool_result",
                            "name": tr["name"],
                            "result": str(tr["result"])[:500],
                        }

                # Final answer produced
                if updates.get("final_answer"):
                    yield {
                        "type": "final",
                        "answer": updates["final_answer"],
                        "iterations": updates.get("iteration", 0),
                    }

    except asyncio.TimeoutError:
        yield {"type": "error", "message": "Agent timed out. Please try a simpler request."}
    except Exception as exc:
        logger.exception("stream_agent failed")
        yield {"type": "error", "message": f"Agent error: {exc}"}


def json_safe_loads(s: str) -> dict:
    import json
    try:
        return json.loads(s)
    except Exception:
        return {}
