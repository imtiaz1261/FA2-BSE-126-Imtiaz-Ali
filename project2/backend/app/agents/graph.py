"""
LangGraph agent graph — Phase 11.

Architecture
------------

    ┌─────────────┐
    │   __start__ │  (entry — state pre-populated by executor)
    └──────┬──────┘
           │
    ┌──────▼──────────┐
    │  classify_intent │  LLM decides: "tools" | "direct" | "clarify"
    └──────┬───────────┘
           │
    ┌──────▼──────┐   intent=="direct" or "clarify"
    │             ├──────────────────────────────────► respond_directly
    │   router    │
    │             ├── intent=="tools" ──────────────► call_llm_with_tools
    └─────────────┘
                                                           │
                                               ┌───────────▼──────────┐
                                               │  call_llm_with_tools  │
                                               │  (binds tool schemas) │
                                               └───────────┬──────────┘
                                                           │
                                         ┌─────────────────▼─────────────────┐
                                         │          tool_router               │
                                         │  has tool_calls? → execute_tools   │
                                         │  else           → synthesise       │
                                         └─────────────────┬─────────────────┘
                                                           │
                                             ┌─────────────▼──────────┐
                                             │     execute_tools       │
                                             │  (runs each tool call)  │
                                             └─────────────┬──────────┘
                                                           │
                                             ┌─────────────▼──────────┐
                                             │   iteration_router      │
                                             │  max reached? → synth   │
                                             │  else        → call_llm │
                                             └─────────────┬──────────┘
                                                           │
                                             ┌─────────────▼──────────┐
                                             │      synthesise         │
                                             │  (final LLM response)   │
                                             └────────────────────────┘

All terminal nodes write `final_answer` into state.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import Any, Dict, List, Literal

from langgraph.graph import END, START, StateGraph

from app.agents.state import AgentState
from app.agents.tool_registry import TOOL_MAP, get_openai_tools
from app.core.config import settings
from app.services.llm_service import get_client

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_INTENT_SYSTEM = """\
You are an intent classifier for an AI research assistant.
Given the user's latest message, decide which path to take:

- "tools"   — the question needs real-time data, calculations, document search,
              web search, or date/time information that you cannot answer reliably
              from memory alone.
- "direct"  — the question is factual, conceptual, or conversational and you can
              answer it accurately from your training knowledge.
- "clarify" — the request is ambiguous and needs clarification before proceeding.

Reply with ONLY one of the three words: tools, direct, or clarify.
"""

_AGENT_SYSTEM = """\
You are a helpful, precise AI research assistant.
You have access to tools: a calculator, date/time utilities, web search,
and document search over the user's uploaded files.
Use tools when you need current information, calculations, or content from
the user's documents.
When you have gathered enough information, give a clear and complete answer.
"""


def _last_user_message(state: AgentState) -> str:
    for msg in reversed(state["messages"]):
        if msg.get("role") == "user":
            return str(msg.get("content", ""))
    return ""


# ---------------------------------------------------------------------------
# Node: classify_intent
# ---------------------------------------------------------------------------


async def classify_intent(state: AgentState) -> Dict[str, Any]:
    """
    Ask the LLM to classify the user's intent as 'tools', 'direct',
    or 'clarify'.  This keeps tool overhead off purely conversational
    exchanges and avoids unnecessary latency.
    """
    user_msg = _last_user_message(state)
    client = get_client()
    try:
        resp = await client.chat.completions.create(
            model=settings.LLM_MODEL,
            temperature=0.0,
            max_tokens=5,
            messages=[
                {"role": "system", "content": _INTENT_SYSTEM},
                {"role": "user", "content": user_msg},
            ],
        )
        raw = (resp.choices[0].message.content or "direct").strip().lower()
        intent = raw if raw in ("tools", "direct", "clarify") else "direct"
    except Exception as exc:
        logger.warning("Intent classification failed (%s) — defaulting to tools", exc)
        intent = "tools"

    logger.debug("Intent classified as: %s", intent)
    return {"intent": intent}


# ---------------------------------------------------------------------------
# Node: respond_directly
# ---------------------------------------------------------------------------


async def respond_directly(state: AgentState) -> Dict[str, Any]:
    """
    Answer the question directly without using any tools.
    Used when intent is 'direct' or 'clarify'.
    """
    client = get_client()
    messages = [{"role": "system", "content": _AGENT_SYSTEM}] + list(state["messages"])
    try:
        resp = await client.chat.completions.create(
            model=settings.LLM_MODEL,
            temperature=settings.LLM_TEMPERATURE,
            messages=messages,
        )
        answer = resp.choices[0].message.content or ""
    except Exception as exc:
        logger.exception("respond_directly LLM call failed")
        answer = f"I encountered an error: {exc}"

    return {
        "final_answer": answer,
        "messages": [{"role": "assistant", "content": answer}],
    }


# ---------------------------------------------------------------------------
# Node: call_llm_with_tools
# ---------------------------------------------------------------------------


async def call_llm_with_tools(state: AgentState) -> Dict[str, Any]:
    """
    Call the LLM with the full tool schema.  The LLM may either return a
    text response (done) or request one or more tool calls.
    """
    tools = get_openai_tools()  # all permitted tools
    client = get_client()
    messages = [{"role": "system", "content": _AGENT_SYSTEM}] + list(state["messages"])

    try:
        resp = await client.chat.completions.create(
            model=settings.LLM_MODEL,
            temperature=settings.LLM_TEMPERATURE,
            messages=messages,
            tools=tools,
            tool_choice="auto",
        )
    except Exception as exc:
        logger.exception("call_llm_with_tools failed")
        return {
            "error": str(exc),
            "final_answer": f"LLM error: {exc}",
        }

    choice = resp.choices[0]
    msg = choice.message

    # Collect tool calls if any
    raw_tool_calls: List[Dict[str, Any]] = []
    if msg.tool_calls:
        for tc in msg.tool_calls:
            raw_tool_calls.append(
                {
                    "id": tc.id,
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,  # JSON string
                }
            )

    # Build the assistant message to append (with tool_calls if present)
    assistant_msg: Dict[str, Any] = {"role": "assistant", "content": msg.content or ""}
    if raw_tool_calls:
        assistant_msg["tool_calls"] = [
            {
                "id": tc["id"],
                "type": "function",
                "function": {"name": tc["name"], "arguments": tc["arguments"]},
            }
            for tc in raw_tool_calls
        ]

    return {
        "tool_calls": raw_tool_calls,
        "messages": [assistant_msg],
        "iteration": state.get("iteration", 0) + 1,
    }


# ---------------------------------------------------------------------------
# Node: execute_tools
# ---------------------------------------------------------------------------


async def execute_tools(state: AgentState) -> Dict[str, Any]:
    """
    Execute every pending tool call and append tool-result messages.
    Handles both sync and async tool functions.
    """
    tool_calls = state.get("tool_calls", [])
    tool_results: List[Dict[str, Any]] = list(state.get("tool_results", []))
    new_messages: List[Dict[str, Any]] = []

    for tc in tool_calls:
        name = tc["name"]
        call_id = tc["id"]
        try:
            args = json.loads(tc.get("arguments", "{}"))
        except json.JSONDecodeError:
            args = {}

        tool_def = TOOL_MAP.get(name)
        if tool_def is None:
            result_content = f"Unknown tool: {name}"
        else:
            # Inject runtime kwargs (db, user_id) if the tool needs them
            injected: Dict[str, Any] = {}
            for key in tool_def.inject:
                val = state.get(key)  # type: ignore[call-overload]
                if val is not None:
                    injected[key] = val

            try:
                if asyncio.iscoroutinefunction(tool_def.fn):
                    result_content = await tool_def.fn(**args, **injected)
                else:
                    result_content = tool_def.fn(**args, **injected)
            except Exception as exc:
                logger.exception("Tool %s raised: %s", name, exc)
                result_content = f"Tool error ({name}): {exc}"

        logger.debug("Tool %s → %s…", name, str(result_content)[:80])
        tool_results.append({"id": call_id, "name": name, "result": result_content})
        new_messages.append(
            {
                "role": "tool",
                "tool_call_id": call_id,
                "name": name,
                "content": str(result_content),
            }
        )

    return {
        "tool_results": tool_results,
        "tool_calls": [],  # clear pending calls after execution
        "messages": new_messages,
    }


# ---------------------------------------------------------------------------
# Node: synthesise
# ---------------------------------------------------------------------------


async def synthesise(state: AgentState) -> Dict[str, Any]:
    """
    Generate the final answer after all tool results are available.
    Called either after execute_tools reaches max iterations or when
    call_llm_with_tools returns text (no tool calls).
    """
    # Check if the last assistant message already contains a final text answer
    for msg in reversed(state["messages"]):
        if msg.get("role") == "assistant" and msg.get("content") and not msg.get("tool_calls"):
            # LLM already gave a plain text response — use it directly
            return {"final_answer": msg["content"]}

    # Otherwise ask the LLM to synthesise based on accumulated tool results
    client = get_client()
    messages = [{"role": "system", "content": _AGENT_SYSTEM}] + list(state["messages"])

    if state.get("iteration", 0) >= state.get("max_iterations", settings.AGENT_MAX_ITERATIONS):
        messages.append(
            {
                "role": "system",
                "content": (
                    "You have used the maximum number of tool iterations. "
                    "Please provide the best answer you can with the information gathered so far."
                ),
            }
        )

    try:
        resp = await client.chat.completions.create(
            model=settings.LLM_MODEL,
            temperature=settings.LLM_TEMPERATURE,
            messages=messages,
        )
        answer = resp.choices[0].message.content or ""
    except Exception as exc:
        logger.exception("synthesise LLM call failed")
        answer = f"I encountered an error generating the final answer: {exc}"

    return {
        "final_answer": answer,
        "messages": [{"role": "assistant", "content": answer}],
    }


# ---------------------------------------------------------------------------
# Routing functions (conditional edges)
# ---------------------------------------------------------------------------


def intent_router(state: AgentState) -> Literal["respond_directly", "call_llm_with_tools"]:
    """Route after intent classification."""
    return (
        "call_llm_with_tools"
        if state.get("intent") == "tools"
        else "respond_directly"
    )


def tool_router(
    state: AgentState,
) -> Literal["execute_tools", "synthesise"]:
    """After call_llm_with_tools: did the LLM request any tool calls?"""
    if state.get("error"):
        return "synthesise"
    return "execute_tools" if state.get("tool_calls") else "synthesise"


def iteration_router(
    state: AgentState,
) -> Literal["call_llm_with_tools", "synthesise"]:
    """After execute_tools: continue looping or force final synthesis?"""
    max_iter = state.get("max_iterations", settings.AGENT_MAX_ITERATIONS)
    if state.get("iteration", 0) >= max_iter:
        logger.warning(
            "Agent reached max iterations (%d) — forcing synthesis", max_iter
        )
        return "synthesise"
    return "call_llm_with_tools"


# ---------------------------------------------------------------------------
# Graph assembly
# ---------------------------------------------------------------------------


def build_graph() -> StateGraph:
    g = StateGraph(AgentState)

    # Nodes
    g.add_node("classify_intent", classify_intent)
    g.add_node("respond_directly", respond_directly)
    g.add_node("call_llm_with_tools", call_llm_with_tools)
    g.add_node("execute_tools", execute_tools)
    g.add_node("synthesise", synthesise)

    # Entry
    g.add_edge(START, "classify_intent")

    # Intent routing
    g.add_conditional_edges(
        "classify_intent",
        intent_router,
        {
            "respond_directly": "respond_directly",
            "call_llm_with_tools": "call_llm_with_tools",
        },
    )

    # Direct response terminates
    g.add_edge("respond_directly", END)

    # Tool routing after LLM call
    g.add_conditional_edges(
        "call_llm_with_tools",
        tool_router,
        {
            "execute_tools": "execute_tools",
            "synthesise": "synthesise",
        },
    )

    # After tool execution: loop or stop
    g.add_conditional_edges(
        "execute_tools",
        iteration_router,
        {
            "call_llm_with_tools": "call_llm_with_tools",
            "synthesise": "synthesise",
        },
    )

    # Synthesis terminates
    g.add_edge("synthesise", END)

    return g


# Compiled graph singleton (compiled once on first import)
_compiled_graph = None


def get_compiled_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph().compile()
    return _compiled_graph
