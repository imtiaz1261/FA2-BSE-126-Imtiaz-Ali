"""
Agent router — Phase 11.

Provides a dedicated endpoint for agent runs, separate from the
messages router, so clients can poll run status or stream agent events
independently of the chat history.

POST /conversations/{id}/agent/run          — full run, returns JSON
POST /conversations/{id}/agent/run/stream   — streams agent events
GET  /conversations/{id}/agent/tools        — list available tools
"""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.message import MessageRole
from app.models.user import User
from app.services import conversation_service, message_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/conversations/{conversation_id}/agent",
    tags=["agent"],
)


def _get_owned_conversation(db: Session, current_user: User, conversation_id: uuid.UUID):
    convo = conversation_service.get_conversation(db, current_user.id, conversation_id)
    if convo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return convo


# ---------------------------------------------------------------------------
# GET /tools — list available tools and their schemas
# ---------------------------------------------------------------------------


@router.get("/tools")
def list_tools(
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    """Return the OpenAI-schema tool list available to the agent."""
    from app.agents.tool_registry import TOOLS

    return [
        {
            "name": t.name,
            "description": t.description,
            "permission": t.permission,
            "parameters": t.parameters,
        }
        for t in TOOLS
    ]


# ---------------------------------------------------------------------------
# POST /run — blocking agent run
# ---------------------------------------------------------------------------


@router.post("/run")
async def run_agent(
    conversation_id: uuid.UUID,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Run the agent to completion and return the full result as JSON.

    Request body: {"content": "user message"}
    """
    _get_owned_conversation(db, current_user, conversation_id)
    user_message = payload.get("content", "").strip()
    if not user_message:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="content must not be empty",
        )

    history = message_service.list_messages(db, conversation_id)
    message_service.add_message(db, conversation_id, MessageRole.USER, user_message)

    from app.agents.executor import run_agent as _run

    result = await _run(
        user_message=user_message,
        user_id=current_user.id,
        conversation_id=conversation_id,
        history=history,
        db=db,
    )

    # Persist assistant reply
    from app.api.messages import _format_tool_summary

    full_content = result.final_answer
    if result.tool_results:
        full_content += _format_tool_summary(result.tool_results)
    message_service.add_message(db, conversation_id, MessageRole.ASSISTANT, full_content)

    return {
        "final_answer": result.final_answer,
        "intent": result.intent,
        "iterations": result.iterations,
        "tool_results": result.tool_results,
        "error": result.error,
    }


# ---------------------------------------------------------------------------
# POST /run/stream — streaming agent events
# ---------------------------------------------------------------------------


@router.post("/run/stream")
async def stream_agent_run(
    conversation_id: uuid.UUID,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    """
    Stream agent events as text/plain with <!--AGENT:{...}--> markers.

    Request body: {"content": "user message"}
    """
    _get_owned_conversation(db, current_user, conversation_id)
    user_message = payload.get("content", "").strip()
    if not user_message:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="content must not be empty",
        )

    history = message_service.list_messages(db, conversation_id)
    message_service.add_message(db, conversation_id, MessageRole.USER, user_message)

    from app.agents.executor import stream_agent
    from app.agents.streaming import format_event
    from app.api.messages import _format_tool_summary

    async def generator():
        final_text = ""
        tool_results_seen = []
        try:
            async for event in stream_agent(
                user_message=user_message,
                user_id=current_user.id,
                conversation_id=conversation_id,
                history=history,
                db=db,
            ):
                yield format_event(event) + "\n"
                if event.get("type") == "final":
                    final_text = event.get("answer", "")
                if event.get("type") == "tool_result":
                    tool_results_seen.append(event)
        except Exception as exc:
            yield format_event({"type": "error", "message": str(exc)}) + "\n"
        finally:
            if final_text:
                summary = _format_tool_summary(tool_results_seen) if tool_results_seen else ""
                message_service.add_message(
                    db,
                    conversation_id,
                    MessageRole.ASSISTANT,
                    final_text + summary,
                )

    return StreamingResponse(generator(), media_type="text/plain")
