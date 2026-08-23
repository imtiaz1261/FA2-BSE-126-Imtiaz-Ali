"""
Messages router.

Phase 6: POST /conversations/{id}/messages — send a message, get the
full LLM reply back in one response, both turns persisted.

Phase 7: POST /conversations/{id}/messages/stream — same thing, but
the assistant's reply streams back as plain-text chunks as the LLM
generates them, and is persisted once the stream completes.
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
from app.schemas.message import MessageCreate, MessageOut
from app.services import conversation_service, message_service, prompts
from app.services.llm_service import LLMServiceError, chat_completion, stream_chat_completion

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/conversations/{conversation_id}/messages", tags=["messages"])


def _get_owned_conversation(db: Session, current_user: User, conversation_id: uuid.UUID):
    conversation = conversation_service.get_conversation(db, current_user.id, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return conversation


@router.get("", response_model=list[MessageOut])
def list_messages(
    conversation_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[MessageOut]:
    _get_owned_conversation(db, current_user, conversation_id)
    messages = message_service.list_messages(db, conversation_id)
    return [MessageOut.model_validate(m) for m in messages]


@router.post("", response_model=MessageOut, status_code=status.HTTP_201_CREATED)
async def send_message(
    conversation_id: uuid.UUID,
    data: MessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MessageOut:
    """Phase 6: non-streaming — waits for the full LLM reply, persists both turns."""
    _get_owned_conversation(db, current_user, conversation_id)

    history = message_service.list_messages(db, conversation_id)
    message_service.add_message(db, conversation_id, MessageRole.USER, data.content)

    llm_messages = prompts.build_messages(history, data.content, data.mode)
    try:
        reply_text = await chat_completion(llm_messages)
    except LLMServiceError as exc:
        logger.error("LLM call failed for conversation %s: %s", conversation_id, exc)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))

    assistant_message = message_service.add_message(
        db, conversation_id, MessageRole.ASSISTANT, reply_text
    )
    return MessageOut.model_validate(assistant_message)


@router.post("/stream")
async def stream_message(
    conversation_id: uuid.UUID,
    data: MessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    """Phase 7: streams the assistant reply as plain-text chunks, persists once done."""
    _get_owned_conversation(db, current_user, conversation_id)

    history = message_service.list_messages(db, conversation_id)
    message_service.add_message(db, conversation_id, MessageRole.USER, data.content)

    llm_messages = prompts.build_messages(history, data.content, data.mode)

    async def event_generator():
        collected: list[str] = []
        try:
            async for chunk in stream_chat_completion(llm_messages):
                collected.append(chunk)
                yield chunk
        except LLMServiceError as exc:
            # Mid-stream (or startup) provider error — surface it as trailing
            # text so the client can show it, rather than failing silently.
            yield f"\n\n[Error: {exc}]"
        finally:
            full_text = "".join(collected).strip()
            if full_text:
                message_service.add_message(db, conversation_id, MessageRole.ASSISTANT, full_text)

    return StreamingResponse(event_generator(), media_type="text/plain")
