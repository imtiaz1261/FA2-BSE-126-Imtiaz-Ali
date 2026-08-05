"""
AgentState — Phase 11.

The single TypedDict that flows through every node in the LangGraph
StateGraph.  LangGraph merges node outputs back into this dict after
each step, so every key that a node may update must be declared here.
"""

from __future__ import annotations

import uuid
from typing import Annotated, Any, Dict, List, Optional

from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class AgentState(TypedDict):
    # ── Identity ──────────────────────────────────────────────────────────────
    user_id: uuid.UUID            # injected before graph.invoke()
    conversation_id: uuid.UUID    # for context / persistence

    # ── Conversation messages (OpenAI format) ─────────────────────────────────
    # add_messages is a LangGraph reducer: new messages are appended, not replaced
    messages: Annotated[List[Dict[str, Any]], add_messages]

    # ── Intent classification result ──────────────────────────────────────────
    intent: Optional[str]         # "tools" | "direct" | "clarify"

    # ── Tool execution trace (for UI transparency) ───────────────────────────
    tool_calls: List[Dict[str, Any]]    # tool calls requested by the LLM
    tool_results: List[Dict[str, Any]]  # results returned by each tool call

    # ── Loop control ──────────────────────────────────────────────────────────
    iteration: int                # incremented each round
    max_iterations: int           # copied from settings at graph entry
    error: Optional[str]          # set on unrecoverable error

    # ── Final answer ─────────────────────────────────────────────────────────
    final_answer: Optional[str]   # populated by the response node
