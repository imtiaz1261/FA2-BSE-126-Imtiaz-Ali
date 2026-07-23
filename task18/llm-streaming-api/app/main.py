"""
FastAPI application entrypoint.

Run with:  uvicorn app.main:app --reload
"""

import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .llm_service import stream_chat_response
from .schemas import ChatStreamRequest
from .streaming_utils import StreamRegistry

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("llm_streaming_api")

app = FastAPI(
    title="Real-Time LLM Streaming API",
    description="Streams LLM responses token-by-token over Server-Sent Events.",
    version="1.0.0",
)

registry = StreamRegistry(max_concurrent=settings.max_concurrent_streams)

app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "active_streams": registry.active_count,
        "max_concurrent_streams": settings.max_concurrent_streams,
        "model": settings.groq_model,
    }


@app.get("/")
async def index():
    from fastapi.responses import FileResponse

    return FileResponse("app/static/index.html")


@app.post("/chat/stream")
async def chat_stream(payload: ChatStreamRequest, request: Request):
    """
    Stream a chat completion as Server-Sent Events.

    Event types sent, in order: start -> (token | heartbeat)* -> usage?
    -> done | cancelled | error | timeout
    """
    if registry.active_count >= settings.max_concurrent_streams:
        raise HTTPException(status_code=503, detail="Server is at max concurrent stream capacity. Try again shortly.")

    request_id = payload.request_id or registry.new_request_id()
    if registry.is_active(request_id):
        raise HTTPException(status_code=409, detail=f"request_id '{request_id}' is already streaming.")

    cancel_event = registry.register(request_id)
    logger.info("Starting stream %s (active=%d)", request_id, registry.active_count)

    async def is_disconnected() -> bool:
        return await request.is_disconnected()

    async def event_source():
        async with registry.semaphore:
            try:
                async for chunk in stream_chat_response(payload, request_id, cancel_event, is_disconnected):
                    yield chunk
            finally:
                registry.unregister(request_id)
                logger.info("Finished stream %s (active=%d)", request_id, registry.active_count)

    return StreamingResponse(
        event_source(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Request-Id": request_id,
            # Disable proxy buffering (e.g. nginx) so chunks flush immediately.
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/chat/cancel/{request_id}")
async def cancel_stream(request_id: str):
    """Cancel an in-flight stream by its request_id."""
    cancelled = registry.cancel(request_id)
    if not cancelled:
        raise HTTPException(status_code=404, detail=f"No active stream with request_id '{request_id}'.")
    return {"cancelled": True, "request_id": request_id}
