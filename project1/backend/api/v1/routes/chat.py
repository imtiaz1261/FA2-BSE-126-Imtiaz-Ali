"""
api/v1/routes/chat.py — Chat Endpoints with SSE Streaming
==========================================================
Routes:
    POST   /chat/stream              Stream a chat response (SSE)
    POST   /chat/conversations       Create a new conversation
    GET    /chat/conversations        List conversations (with search)
    GET    /chat/conversations/{id}   Get messages in a conversation
    PATCH  /chat/conversations/{id}   Rename a conversation
    DELETE /chat/conversations/{id}   Delete a conversation
"""

import uuid
from typing import Optional, AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.dependencies import get_current_active_user, get_db
from backend.db.models.user import User
from backend.schemas.chat import (
    ChatRequest,
    ConversationCreate,
    ConversationListResponse,
    ConversationRename,
    ConversationResponse,
    MessageListResponse,
    MessageResponse,
)
from backend.services import chat_service
from backend.core.logging import get_logger

router = APIRouter(prefix="/chat", tags=["Chat"])
logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# SSE streaming endpoint
# ---------------------------------------------------------------------------

@router.post("/stream", summary="Stream a chat response (Server-Sent Events)")
async def stream_chat(
    body: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> StreamingResponse:
    """
    Send a message and receive a streaming response via SSE.

    **SSE frame types returned:**
    - `data: <token>` — streamed response token
    - `data: [CONV_ID]<uuid>` — conversation ID (first frame)
    - `data: [DONE]` — stream finished
    - `data: [ERROR]<message>` — LLM error
    - `data: [LIMIT]<message>` — usage limit reached
    - `data: [BLOCKED]<message>` — guardrail blocked
    - `data: [REPLACE]<message>` — output guardrail replaced content

    The client should:
    1. Read the `[CONV_ID]` frame and store it for subsequent requests
    2. Accumulate tokens until `[DONE]`
    3. Handle `[ERROR]`, `[LIMIT]`, `[BLOCKED]` as error states
    """
    return StreamingResponse(
        chat_service.stream_chat_response(
            db=db,
            user=current_user,
            user_message=body.message,
            conversation_id=body.conversation_id,
            mode=body.mode,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
            "Connection": "keep-alive",
        },
    )


# ---------------------------------------------------------------------------
# Conversation CRUD
# ---------------------------------------------------------------------------

@router.post(
    "/conversations",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new conversation",
)
async def create_conversation(
    body: ConversationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ConversationResponse:
    conv = await chat_service.create_conversation(
        db, current_user.id, title=body.title, feature=body.feature
    )
    return ConversationResponse.model_validate(conv)


@router.get(
    "/conversations",
    response_model=ConversationListResponse,
    summary="List conversations",
)
async def list_conversations(
    search: Optional[str] = Query(None, description="Search by title"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ConversationListResponse:
    convs, total = await chat_service.list_conversations(
        db, current_user.id, search=search, limit=limit, offset=offset
    )
    return ConversationListResponse(
        conversations=[ConversationResponse.model_validate(c) for c in convs],
        total=total,
    )


@router.get(
    "/conversations/{conv_id}",
    response_model=MessageListResponse,
    summary="Get messages in a conversation",
)
async def get_conversation_messages(
    conv_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> MessageListResponse:
    msgs = await chat_service.get_messages(db, conv_id, current_user.id)
    if not msgs and not await chat_service.get_conversation(db, conv_id, current_user.id):
        raise HTTPException(status_code=404, detail="Conversation not found")
    return MessageListResponse(
        messages=[
            MessageResponse(
                id=m.id,
                conversation_id=m.conversation_id,
                role=m.role.value,
                content=m.content,
                token_count=m.token_count,
                model=m.model,
                metadata_=m.metadata_,
                created_at=m.created_at,
            )
            for m in msgs
        ],
        conversation_id=conv_id,
    )


@router.patch(
    "/conversations/{conv_id}",
    response_model=ConversationResponse,
    summary="Rename a conversation",
)
async def rename_conversation(
    conv_id: uuid.UUID,
    body: ConversationRename,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ConversationResponse:
    conv = await chat_service.rename_conversation(
        db, conv_id, current_user.id, body.title
    )
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return ConversationResponse.model_validate(conv)


@router.delete(
    "/conversations/{conv_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a conversation",
)
async def delete_conversation(
    conv_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> None:
    deleted = await chat_service.delete_conversation(db, conv_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")


@router.post("/agent/stream", summary="Stream an AI Agent response (LangGraph ReAct)")
async def stream_agent(
    body: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> StreamingResponse:
    """
    Run the LangGraph ReAct agent with tool calling and stream the response.

    The agent can use: Calculator, Web Search, Date/Time, Weather, Document Search.

    SSE frame types:
    - `data: [TOOL]<name>:<input>` — agent calling a tool
    - `data: [OBSERVATION]<result>` — tool result
    - `data: <token>` — final answer tokens
    - `data: [DONE]` / `[ERROR]` / `[LIMIT]` / `[BLOCKED]`
    """
    from backend.ai.agents.orchestrator import stream_agent_response
    return StreamingResponse(
        stream_agent_response(
            db=db,
            user=current_user,
            user_message=body.message,
            conversation_id=body.conversation_id,
        ),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/ping", include_in_schema=False)
async def ping():
    return {"router": "chat", "status": "ok"}
