"""
POST /chat/stream — streams the assistant's reply token-by-token as
Server-Sent Events. POST /chat/stream/{message_id}/stop — cancels an
in-flight generation.

SSE event shapes (each line is `data: <json>\n\n`):
  {"type": "start", "message_id": "..."}
  {"type": "token", "content": "..."}         (repeated)
  {"type": "done", "message_id": "..."}
  {"type": "error", "message": "..."}

Why a separate /stop endpoint AND disconnect detection: a stop button click
should cancel generation even if, for some reason, the SSE connection is
still technically open (e.g. behind a buffering proxy) — and a disconnect
(tab closed, network drop) should also stop wasted LLM calls even if the
client never got to click stop.

Memory Integration:
- At conversation start, retrieve relevant memories based on opening message
- Inject retrieved memories into system prompt as hidden context
- Update access statistics for memory analytics
"""
import asyncio
import json
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.llm_service import stream_llm_response
from app.models import User, Message, Conversation, MessageRole
from app.schemas_chat import ChatStreamRequest, StopGenerationResponse
from app.services.memory_context_injector import MemoryContextInjector
from app.middleware.usage_limiter import enforce_usage_limit, increment_usage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])

# In-memory registry of in-flight generations: message_id -> cancel Event.
# Fine for a single-process dev/small deployment; for multi-worker production,
# back this with Redis (SET message_id "1" EX 300) instead so a stop request
# hitting a different worker process still reaches the right generation.
_active_generations: dict[str, asyncio.Event] = {}


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


@router.post("/stream")
async def chat_stream(
    payload: ChatStreamRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    usage_info: dict = Depends(enforce_usage_limit),
):
    """
    Stream chat responses with memory context and usage quota enforcement.
    
    Dependencies:
    - enforce_usage_limit: Blocks if daily quota exceeded (returns 429)
    - Memory injection: Retrieves and injects relevant user memories
    """
    message_id = str(uuid.uuid4())
    cancel_event = asyncio.Event()
    _active_generations[message_id] = cancel_event

    # Inject memory context into system prompt
    messages = payload.messages.copy()
    try:
        injector = MemoryContextInjector()
        messages = await injector.inject_memory_context(
            messages=messages,
            user_id=str(current_user.id),
            db=db,
            conversation_id=payload.conversation_id,
        )
    except Exception as e:
        # Don't fail the chat if memory injection errors
        logger.error(f"Memory context injection failed: {e}", exc_info=True)

    async def event_generator():
        try:
            yield _sse({"type": "start", "message_id": message_id})
            async for chunk in stream_llm_response(messages, cancel_event):
                # Stop as soon as the client goes away, without waiting for
                # the next chunk from the LLM to notice.
                if await request.is_disconnected():
                    cancel_event.set()
                    break
                yield _sse({"type": "token", "content": chunk})

            if cancel_event.is_set():
                yield _sse({"type": "stopped", "message_id": message_id})
            else:
                yield _sse({"type": "done", "message_id": message_id})
                # Increment usage counter after successful generation
                await increment_usage(current_user, db, count=1)
        except Exception as exc:  # noqa: BLE001 — surface to client, then re-log upstream
            yield _sse({"type": "error", "message": "Generation failed. Please try again."})
            raise exc
        finally:
            _active_generations.pop(message_id, None)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            # Disable buffering on nginx-style proxies so tokens flush immediately.
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.post("/stream/{message_id}/stop", response_model=StopGenerationResponse)
async def stop_generation(
    message_id: str, current_user: User = Depends(get_current_user)
):
    cancel_event = _active_generations.get(message_id)
    if cancel_event is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "No active generation with that id (it may have already finished).",
        )
    cancel_event.set()
    return StopGenerationResponse(message="Stop signal sent.", stopped=True)
