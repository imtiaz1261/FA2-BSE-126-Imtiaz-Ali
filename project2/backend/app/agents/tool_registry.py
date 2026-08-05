"""
Tool registry — Phase 12.

Central catalog of every tool available to the LangGraph agent.

Each entry is a ToolDef that describes:
  - name          : identifier the LLM uses in tool_calls
  - description   : shown to the LLM in the function schema
  - parameters    : JSON-Schema compatible dict for the function arguments
  - permission    : "free" (always allowed) | "user_docs" (requires docs)
                    | "web" (requires TAVILY_API_KEY)
  - fn            : the Python callable (sync or async)
  - inject        : optional list of extra kwargs injected at run-time
                    (db, user_id) rather than by the LLM

The registry also builds the `tools` list in OpenAI function-calling
format so it can be passed directly to `client.chat.completions.create`.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# ToolDef dataclass
# ---------------------------------------------------------------------------


@dataclass
class ToolDef:
    name: str
    description: str
    parameters: dict          # JSON-Schema object for the tool's arguments
    fn: Callable
    permission: str = "free"  # "free" | "user_docs" | "web"
    inject: List[str] = field(default_factory=list)  # runtime-injected kwargs


# ---------------------------------------------------------------------------
# Individual tool imports (lazy — avoids circular imports at module load)
# ---------------------------------------------------------------------------


def _calc(expression: str) -> str:
    from app.agents.tools.calculator import calculate
    return calculate(expression)


def _datetime(timezone_name: str = "UTC") -> str:
    from app.agents.tools.datetime_tool import get_current_datetime
    return get_current_datetime(timezone_name)


def _add_days(date_str: str, days: int) -> str:
    from app.agents.tools.datetime_tool import add_days
    return add_days(date_str, int(days))


def _days_between(date_a: str, date_b: str) -> str:
    from app.agents.tools.datetime_tool import days_between
    return days_between(date_a, date_b)


def _day_of_week(date_str: str) -> str:
    from app.agents.tools.datetime_tool import day_of_week
    return day_of_week(date_str)


def _web_search(query: str, max_results: int = 5) -> str:
    from app.agents.tools.web_search import web_search
    return web_search(query, max_results)


async def _doc_search(query: str, db: Session, user_id: uuid.UUID, top_k: int = 5) -> str:
    from app.agents.tools.document_search import document_search
    return await document_search(query, db=db, user_id=user_id, top_k=top_k)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

TOOLS: List[ToolDef] = [
    # ── Calculator ───────────────────────────────────────────────────────────
    ToolDef(
        name="calculator",
        description=(
            "Evaluate a mathematical expression and return the numeric result. "
            "Supports +, -, *, /, //, %, **, parentheses, and functions like "
            "sqrt(), abs(), round(), log(), sin(), cos(), tan(), floor(), ceil(). "
            "Use this for any arithmetic or mathematical question."
        ),
        parameters={
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "A math expression, e.g. '2 + 2', 'sqrt(144)', '(3**10) / 7'",
                }
            },
            "required": ["expression"],
        },
        fn=_calc,
        permission="free",
    ),

    # ── Date/Time ────────────────────────────────────────────────────────────
    ToolDef(
        name="get_current_datetime",
        description="Return the current UTC date and time. Use when the user asks what time or date it is.",
        parameters={
            "type": "object",
            "properties": {
                "timezone_name": {
                    "type": "string",
                    "description": "Timezone label to display, default 'UTC'.",
                    "default": "UTC",
                }
            },
            "required": [],
        },
        fn=_datetime,
        permission="free",
    ),
    ToolDef(
        name="add_days",
        description=(
            "Add or subtract a number of days from an ISO date and return the resulting date. "
            "Use negative days to go back in time."
        ),
        parameters={
            "type": "object",
            "properties": {
                "date_str": {
                    "type": "string",
                    "description": "ISO date string, e.g. '2026-08-03'",
                },
                "days": {
                    "type": "integer",
                    "description": "Number of days to add (negative to subtract)",
                },
            },
            "required": ["date_str", "days"],
        },
        fn=_add_days,
        permission="free",
    ),
    ToolDef(
        name="days_between",
        description="Calculate the number of days between two ISO dates.",
        parameters={
            "type": "object",
            "properties": {
                "date_a": {"type": "string", "description": "Start ISO date"},
                "date_b": {"type": "string", "description": "End ISO date"},
            },
            "required": ["date_a", "date_b"],
        },
        fn=_days_between,
        permission="free",
    ),
    ToolDef(
        name="day_of_week",
        description="Return the day of the week for a given ISO date string.",
        parameters={
            "type": "object",
            "properties": {
                "date_str": {
                    "type": "string",
                    "description": "ISO date string, e.g. '2026-08-03'",
                }
            },
            "required": ["date_str"],
        },
        fn=_day_of_week,
        permission="free",
    ),

    # ── Web search ────────────────────────────────────────────────────────────
    ToolDef(
        name="web_search",
        description=(
            "Search the web for current, real-time information. "
            "Use when the user asks about recent events, news, prices, or anything "
            "that requires up-to-date information beyond your training data."
        ),
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query string",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Number of results to return (1-10, default 5)",
                    "default": 5,
                },
            },
            "required": ["query"],
        },
        fn=_web_search,
        permission="web",
    ),

    # ── Document search ────────────────────────────────────────────────────────
    ToolDef(
        name="document_search",
        description=(
            "Search the user's uploaded documents for relevant content. "
            "Use when the user asks questions that might be answered by their "
            "personal knowledge base, uploaded files, or research documents."
        ),
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural-language search query",
                },
                "top_k": {
                    "type": "integer",
                    "description": "Number of document chunks to retrieve (default 5)",
                    "default": 5,
                },
            },
            "required": ["query"],
        },
        fn=_doc_search,
        permission="user_docs",
        inject=["db", "user_id"],  # injected at run-time by the executor
    ),
]

# Name → ToolDef lookup map
TOOL_MAP: dict[str, ToolDef] = {t.name: t for t in TOOLS}


# ---------------------------------------------------------------------------
# OpenAI function-calling schema builder
# ---------------------------------------------------------------------------


def get_openai_tools(
    allowed_permissions: Optional[set[str]] = None,
) -> List[dict]:
    """
    Return the tools list in OpenAI function-calling format.

    Args:
        allowed_permissions: If provided, only include tools whose permission
                             level is in this set.  Pass None to include all.
    """
    result = []
    for t in TOOLS:
        if allowed_permissions and t.permission not in allowed_permissions:
            continue
        result.append(
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                },
            }
        )
    return result


def get_tool(name: str) -> Optional[ToolDef]:
    """Look up a ToolDef by name.  Returns None if not found."""
    return TOOL_MAP.get(name)
