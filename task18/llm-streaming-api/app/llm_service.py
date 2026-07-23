"""
Core streaming logic.

The tricky part of "stream tokens AND send heartbeats" is that these are
two independent sources of events happening on different schedules. The
pattern used here:

1. A background task (_produce_tokens) pulls tokens from the Groq stream
   and pushes them onto an asyncio.Queue as they arrive.
2. The main generator (stream_chat_response) pulls from that queue with a
   timeout equal to the heartbeat interval. If nothing arrives in time, it
   emits a heartbeat and loops again -- so heartbeats only fire during
   genuine gaps, not on a fixed clock that fights with real tokens.
3. Cancellation, client disconnect, and the overall request timeout are all
   checked on every loop iteration.
"""

import asyncio
import logging
import time

from groq import APIError, AsyncGroq

from .config import settings
from .schemas import ChatStreamRequest
from .streaming_utils import sse_event

logger = logging.getLogger("llm_streaming_api")

_SENTINEL_DONE = object()
_SENTINEL_ERROR = object()

_client = AsyncGroq(api_key=settings.groq_api_key) if settings.groq_api_key else None


async def _produce_tokens(request: ChatStreamRequest, queue: "asyncio.Queue"):
    """Background task: pull tokens from Groq and push them onto the queue."""
    if _client is None:
        await queue.put((_SENTINEL_ERROR, "GROQ_API_KEY is not configured on the server."))
        return

    model = request.model or settings.groq_model
    messages = [m.model_dump() for m in request.messages]

    try:
        stream = await _client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            token = getattr(delta, "content", None) if delta else None
            if token:
                await queue.put(("token", token))

            # Groq's final chunk in a stream carries an `x_groq.usage` field
            # with real token counts -- capture it if present.
            usage = getattr(chunk, "x_groq", None)
            if usage and getattr(usage, "usage", None):
                await queue.put(("usage", usage.usage.model_dump()))

        await queue.put((_SENTINEL_DONE, None))

    except APIError as exc:
        logger.exception("Groq API error during streaming")
        await queue.put((_SENTINEL_ERROR, f"LLM provider error: {exc}"))
    except asyncio.CancelledError:
        raise
    except Exception as exc:  # last-resort guard -- never let this task die silently
        logger.exception("Unexpected error during token production")
        await queue.put((_SENTINEL_ERROR, f"Unexpected server error: {exc}"))


async def stream_chat_response(
    request: ChatStreamRequest,
    request_id: str,
    cancel_event: asyncio.Event,
    is_disconnected,
):
    """
    Async generator yielding SSE-formatted strings.

    Yields, in order:
      - one 'start' event
      - many 'token' events, one per chunk of generated text
      - occasional 'heartbeat' events during quiet gaps
      - a final 'usage' event with token counts (if the provider reports them)
      - exactly one of: 'done', 'cancelled', 'error', or 'timeout'
    """
    queue: asyncio.Queue = asyncio.Queue()
    producer = asyncio.create_task(_produce_tokens(request, queue))

    start_time = time.monotonic()
    full_text_parts: list[str] = []
    usage_stats: dict | None = None

    yield sse_event("start", {"request_id": request_id, "model": request.model or settings.groq_model})

    try:
        while True:
            # -- hard timeout guard --
            elapsed = time.monotonic() - start_time
            if elapsed > settings.request_timeout_seconds:
                logger.warning("Stream %s exceeded timeout after %.1fs", request_id, elapsed)
                yield sse_event("timeout", {"message": "Generation timed out."})
                return

            # -- client disconnect guard --
            if await is_disconnected():
                logger.info("Client disconnected for stream %s", request_id)
                return

            # -- cancellation guard --
            if cancel_event.is_set():
                logger.info("Stream %s cancelled by client request", request_id)
                yield sse_event("cancelled", {"message": "Generation cancelled by request."})
                return

            timeout_left = max(settings.request_timeout_seconds - elapsed, 0.1)
            wait_for = min(settings.heartbeat_interval_seconds, timeout_left)

            try:
                kind, payload = await asyncio.wait_for(queue.get(), timeout=wait_for)
            except asyncio.TimeoutError:
                yield sse_event("heartbeat", {"t": int(time.time())})
                continue

            if kind == "token":
                full_text_parts.append(payload)
                yield sse_event("token", {"text": payload})
            elif kind == "usage":
                usage_stats = payload
            elif kind is _SENTINEL_DONE:
                if usage_stats:
                    yield sse_event("usage", usage_stats)
                yield sse_event(
                    "done",
                    {"message": "Stream complete.", "total_chars": sum(len(p) for p in full_text_parts)},
                )
                return
            elif kind is _SENTINEL_ERROR:
                yield sse_event("error", {"message": payload})
                return

    finally:
        if not producer.done():
            producer.cancel()
