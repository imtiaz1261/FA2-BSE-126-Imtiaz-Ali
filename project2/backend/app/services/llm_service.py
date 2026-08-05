"""
Centralized LLM provider service — Phase 6/7 + Phase 17 (Langfuse tracing).

Every LLM call goes through this module.  Phase 17 wraps each call with
a Langfuse generation so token counts, latency, and model metadata are
recorded automatically in the Langfuse dashboard.

Tracing is fully optional — all Langfuse calls are guarded so the
service works identically when keys are not configured.
"""

import logging
import time
from typing import AsyncGenerator, Optional

from openai import APIError, APIStatusError, AsyncOpenAI, AuthenticationError

from app.core.config import settings

logger = logging.getLogger(__name__)


class LLMServiceError(Exception):
    """Raised for any provider-facing error, with a user-safe message already set."""


def get_client() -> AsyncOpenAI:
    if not settings.OPENAI_API_KEY:
        raise LLMServiceError(
            "No LLM API key configured. Set OPENAI_API_KEY in your .env file."
        )
    return AsyncOpenAI(api_key=settings.OPENAI_API_KEY, base_url=settings.OPENAI_BASE_URL)


def _safe_error(exc: Exception) -> str:
    if isinstance(exc, AuthenticationError):
        return "LLM provider rejected the API key. Check OPENAI_API_KEY in .env."
    if isinstance(exc, APIStatusError):
        return f"LLM provider returned an error ({exc.status_code})."
    if isinstance(exc, APIError):
        return "LLM provider error. Please try again."
    return "Unexpected error talking to the LLM."


async def chat_completion(
    messages: list[dict],
    trace=None,
    generation_name: str = "llm-completion",
    user_id: Optional[str] = None,
) -> str:
    """
    Single non-streaming completion.  Returns the assistant's full reply text.

    Phase 17: if a Langfuse trace is provided (or created internally when lf
    is configured), records a generation with input/output/usage/latency.
    """
    from app.services.langfuse_service import (
        finish_generation,
        get_langfuse,
        start_generation,
    )

    lf = get_langfuse()
    # Use provided trace or create a standalone one
    _own_trace = False
    if trace is None and lf is not None:
        from app.services.langfuse_service import create_trace
        trace = create_trace(lf, name="chat_completion", user_id=user_id)
        _own_trace = True

    gen = start_generation(
        trace,
        name=generation_name,
        model=settings.LLM_MODEL,
        input_messages=messages,
    )

    client = get_client()
    t0 = time.monotonic()
    try:
        response = await client.chat.completions.create(
            model=settings.LLM_MODEL,
            temperature=settings.LLM_TEMPERATURE,
            messages=messages,
        )
    except Exception as exc:
        logger.exception("LLM chat_completion failed")
        if gen:
            finish_generation(gen, output=f"ERROR: {exc}")
        raise LLMServiceError(_safe_error(exc)) from exc

    latency_ms = int((time.monotonic() - t0) * 1000)
    content = response.choices[0].message.content or ""

    # Extract usage for Langfuse + cost tracking
    usage_data = None
    prompt_tokens = 0
    completion_tokens = 0
    if response.usage:
        prompt_tokens = response.usage.prompt_tokens or 0
        completion_tokens = response.usage.completion_tokens or 0
        usage_data = {
            "input": prompt_tokens,
            "output": completion_tokens,
            "total": response.usage.total_tokens or 0,
            "unit": "TOKENS",
        }

    finish_generation(
        gen,
        output=content,
        usage=usage_data,
        metadata={"latency_ms": latency_ms, "model": settings.LLM_MODEL},
    )

    if _own_trace:
        from app.services.langfuse_service import flush
        flush(lf)

    # Attach usage info to the return so callers can record it
    response._prompt_tokens = prompt_tokens  # type: ignore[attr-defined]
    response._completion_tokens = completion_tokens  # type: ignore[attr-defined]

    return content


async def stream_chat_completion(
    messages: list[dict],
    trace=None,
    generation_name: str = "llm-stream",
) -> AsyncGenerator[str, None]:
    """
    Streaming completion.  Yields text deltas.

    Phase 17: records a generation with full output accumulated after the
    stream completes.  Token counts are estimated from output length when
    the provider does not return usage in streaming mode.
    """
    from app.services.langfuse_service import finish_generation, get_langfuse, start_generation

    lf = get_langfuse()
    _own_trace = False
    if trace is None and lf is not None:
        from app.services.langfuse_service import create_trace
        trace = create_trace(lf, name="stream_chat_completion")
        _own_trace = True

    gen = start_generation(
        trace,
        name=generation_name,
        model=settings.LLM_MODEL,
        input_messages=messages,
    )

    client = get_client()
    t0 = time.monotonic()
    try:
        stream = await client.chat.completions.create(
            model=settings.LLM_MODEL,
            temperature=settings.LLM_TEMPERATURE,
            messages=messages,
            stream=True,
        )
    except Exception as exc:
        logger.exception("LLM stream_chat_completion failed to start")
        if gen:
            finish_generation(gen, output=f"ERROR: {exc}")
        raise LLMServiceError(_safe_error(exc)) from exc

    collected_chunks: list[str] = []
    try:
        async for chunk in stream:
            delta = chunk.choices[0].delta.content if chunk.choices else None
            if delta:
                collected_chunks.append(delta)
                yield delta
    except Exception:
        logger.exception("LLM stream interrupted mid-response")
        return
    finally:
        latency_ms = int((time.monotonic() - t0) * 1000)
        full_output = "".join(collected_chunks)
        # Estimate tokens (4 chars ≈ 1 token)
        approx_output_tokens = max(1, len(full_output) // 4)
        approx_input_tokens = max(1, sum(len(str(m.get("content", ""))) for m in messages) // 4)

        finish_generation(
            gen,
            output=full_output,
            usage={
                "input": approx_input_tokens,
                "output": approx_output_tokens,
                "total": approx_input_tokens + approx_output_tokens,
                "unit": "TOKENS",
            },
            metadata={"latency_ms": latency_ms, "model": settings.LLM_MODEL, "streamed": True},
        )
        if _own_trace:
            from app.services.langfuse_service import flush
            flush(lf)
