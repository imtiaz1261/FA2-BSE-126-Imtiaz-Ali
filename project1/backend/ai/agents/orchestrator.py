"""
ai/agents/orchestrator.py — LangGraph ReAct Agent
===================================================
Implements a ReAct (Reason + Act) agent using LangGraph.

Loop:
    User Input
        ↓
    LLM decides: answer directly OR call a tool
        ↓ (if tool)
    Execute tool → get Observation
        ↓
    LLM reasons over observation
        ↓ (repeat until no more tool calls)
    Final Answer
        ↓
    Output Guardrail
        ↓
    Stream to user
"""

from __future__ import annotations
import time
import uuid
from typing import AsyncGenerator, Optional

from backend.core.config import settings
from backend.core.logging import get_logger
from backend.ai.guardrails.input_guard import check_input
from backend.ai.guardrails.output_guard import check_output

logger = get_logger(__name__)


def build_tools(collection_name: Optional[str] = None) -> list:
    """Build the tool list for the agent."""
    from langchain.tools import tool
    from backend.ai.agents.tools.calculator_tool import calculator
    from backend.ai.agents.tools.search_tool import web_search
    from backend.ai.agents.tools.datetime_tool import get_datetime
    from backend.ai.agents.tools.weather_tool import get_weather
    from backend.ai.agents.tools.document_tool import search_documents_sync

    @tool
    def calculator_tool(expression: str) -> str:
        """Evaluate mathematical expressions. Input: a math expression like '2 + 2' or 'sqrt(16)'."""
        return calculator(expression)

    @tool
    def web_search_tool(query: str) -> str:
        """Search the web for current information. Use for recent events, facts, or anything needing live data."""
        return web_search(query)

    @tool
    def datetime_tool(timezone_name: str = "UTC") -> str:
        """Get the current date and time. Optionally specify a timezone like 'US/Eastern' or 'Europe/London'."""
        return get_datetime(timezone_name)

    @tool
    def weather_tool(location: str) -> str:
        """Get current weather for a city or location. Input: city name like 'London' or 'New York'."""
        return get_weather(location)

    tools = [calculator_tool, web_search_tool, datetime_tool, weather_tool]

    # Document search tool — only added when the user has a collection
    if collection_name:
        @tool
        def document_search_tool(question: str) -> str:
            """Search the user's uploaded documents for relevant information. Use when asked about document content."""
            return search_documents_sync(question, collection_name)
        tools.append(document_search_tool)

    return tools


async def stream_agent_response(
    db,
    user,
    user_message: str,
    conversation_id: Optional[uuid.UUID] = None,
) -> AsyncGenerator[str, None]:
    """
    Run the LangGraph agent and stream output as SSE frames.

    Yields the same SSE frame types as chat_service.stream_chat_response:
        data: [CONV_ID]<uuid>
        data: <token>
        data: [TOOL]<tool_name>:<input>
        data: [OBSERVATION]<result>
        data: [BLOCKED]<reason>
        data: [LIMIT]<reason>
        data: [ERROR]<message>
        data: [DONE]
    """
    start = time.monotonic()

    from backend.db.models.usage import AIFeature, RequestStatus
    from backend.services.usage_service import check_limits, log_usage
    from backend.services.chat_service import (
        create_conversation, get_conversation,
        get_messages, _save_message, _build_history,
    )
    from backend.db.models.conversation import MessageRole
    from backend.ai.llm import get_llm, count_tokens
    from backend.ai.rag.vector_store import get_user_collection_name

    feature = AIFeature.AGENT

    # Enforcement gate
    limit_status = await check_limits(db, user.id, feature)
    if not limit_status.allowed:
        await log_usage(db, user.id, feature, 0, 0, settings.OPENAI_MODEL,
                        status=RequestStatus.BLOCKED, error_message=limit_status.reason)
        yield f"data: [LIMIT]{limit_status.reason}\n\n"
        yield "data: [DONE]\n\n"
        return

    # Input guardrail
    guard = check_input(user_message)
    if not guard.safe:
        await log_usage(db, user.id, feature, 0, 0, settings.OPENAI_MODEL,
                        status=RequestStatus.GUARDRAIL_BLOCKED, error_message=guard.reason)
        yield f"data: [BLOCKED]{guard.reason}\n\n"
        yield "data: [DONE]\n\n"
        return

    # Ensure conversation
    if conversation_id:
        conv = await get_conversation(db, conversation_id, user.id)
        if not conv:
            conversation_id = None
    if not conversation_id:
        conv = await create_conversation(db, user.id, feature="agent")
        conversation_id = conv.id

    yield f"data: [CONV_ID]{conversation_id}\n\n"

    # Save user message
    prompt_tokens = count_tokens(user_message)
    await _save_message(db, conversation_id, MessageRole.USER,
                        user_message, token_count=prompt_tokens)

    # Build tools
    collection_name = get_user_collection_name(user.id)
    tools = build_tools(collection_name=collection_name)

    # Build LangGraph agent
    try:
        from langgraph.prebuilt import create_react_agent
        from langchain_core.messages import HumanMessage, SystemMessage

        llm = get_llm(streaming=False)
        llm_with_tools = llm.bind_tools(tools)

        agent = create_react_agent(llm, tools)

        # Build history
        history_msgs = await get_messages(db, conversation_id, user.id)
        lc_history = _build_history(history_msgs[:-1])  # Exclude the message we just saved

        messages = [HumanMessage(content=user_message)]

        # Run agent
        full_response = ""
        tool_calls_count = 0
        tool_metadata = []

        async for event in agent.astream(
            {"messages": messages},
            stream_mode="values",
        ):
            msgs = event.get("messages", [])
            if not msgs:
                continue

            last = msgs[-1]

            # Tool calls
            if hasattr(last, "tool_calls") and last.tool_calls:
                for tc in last.tool_calls:
                    tool_name = tc.get("name", "tool")
                    tool_input = str(tc.get("args", {}))[:200]
                    yield f"data: [TOOL]{tool_name}:{tool_input}\n\n"
                    tool_calls_count += 1
                    tool_metadata.append({"tool": tool_name, "input": tool_input})

            # Tool result (ToolMessage)
            elif hasattr(last, "type") and last.type == "tool":
                observation = str(last.content)[:500]
                yield f"data: [OBSERVATION]{observation}\n\n"

            # Final AI response
            elif hasattr(last, "type") and last.type == "ai" and last.content and not getattr(last, "tool_calls", None):
                full_response = last.content

    except Exception as exc:
        logger.error("agent_error", error=str(exc), user_id=str(user.id))
        full_response = f"I encountered an error while processing your request. Please try again.\n\nDetails: {str(exc)[:200]}"
        error_msg = str(exc)
        await log_usage(db, user.id, feature, prompt_tokens, 0, settings.OPENAI_MODEL,
                        status=RequestStatus.ERROR, latency_ms=int((time.monotonic()-start)*1000),
                        conversation_id=conversation_id, error_message=error_msg)
        yield f"data: [ERROR]{full_response}\n\n"
        yield "data: [DONE]\n\n"
        return

    # Output guardrail
    out_guard = check_output(full_response)
    final_content = out_guard.content

    # Stream final content
    for token in final_content.split(" "):
        yield f"data: {token} \n\n"

    # Save assistant message
    completion_tokens = count_tokens(final_content)
    metadata = {"tool_calls": tool_metadata} if tool_metadata else None
    await _save_message(db, conversation_id, MessageRole.ASSISTANT,
                        final_content, token_count=completion_tokens,
                        model=settings.OPENAI_MODEL, metadata=metadata)

    # Log usage
    latency = int((time.monotonic() - start) * 1000)
    await log_usage(db, user.id, feature, prompt_tokens, completion_tokens,
                    settings.OPENAI_MODEL, latency_ms=latency,
                    status=RequestStatus.SUCCESS, conversation_id=conversation_id)

    # Log tool calls separately
    if tool_calls_count > 0:
        for _ in range(tool_calls_count):
            await log_usage(db, user.id, AIFeature.TOOL_CALL, 0, 0,
                            settings.OPENAI_MODEL, status=RequestStatus.SUCCESS,
                            conversation_id=conversation_id)

    yield "data: [DONE]\n\n"
    logger.info("agent_complete", user_id=str(user.id), tool_calls=tool_calls_count,
                latency_ms=latency)
