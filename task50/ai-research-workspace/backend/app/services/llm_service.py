"""
Centralized LLM provider service.

Every place in the app that needs to talk to an LLM goes through this
module instead of instantiating an OpenAI client directly, so the
provider, model, and error handling stay in one place. Swapping
providers (OpenAI -> Groq -> local) only requires changing `.env`
since Groq and most "OpenAI-compatible" providers implement the same
`/v1/chat/completions` shape.
"""

import logging
from typing import AsyncGenerator

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


async def chat_completion(messages: list[dict]) -> str:
    """Phase 6: single non-streaming completion. Returns the assistant's full reply text."""
    client = get_client()
    try:
        response = await client.chat.completions.create(
            model=settings.LLM_MODEL,
            temperature=settings.LLM_TEMPERATURE,
            messages=messages,
        )
    except Exception as exc:
        logger.exception("LLM chat_completion failed")
        raise LLMServiceError(_safe_error(exc)) from exc

    content = response.choices[0].message.content
    return content or ""


async def stream_chat_completion(messages: list[dict]) -> AsyncGenerator[str, None]:
    """
    Phase 7: streaming completion. Yields text chunks (deltas) as they
    arrive from the provider. Raises LLMServiceError before any chunk
    is yielded if the request itself fails (e.g. bad API key); errors
    that occur mid-stream are logged and the stream ends cleanly so
    the client always gets whatever was generated so far.
    """
    client = get_client()
    try:
        stream = await client.chat.completions.create(
            model=settings.LLM_MODEL,
            temperature=settings.LLM_TEMPERATURE,
            messages=messages,
            stream=True,
        )
    except Exception as exc:
        logger.exception("LLM stream_chat_completion failed to start")
        raise LLMServiceError(_safe_error(exc)) from exc

    try:
        async for chunk in stream:
            delta = chunk.choices[0].delta.content if chunk.choices else None
            if delta:
                yield delta
    except Exception:
        logger.exception("LLM stream interrupted mid-response")
        # Don't raise here — the caller has likely already sent partial
        # content to the client. Just end the stream.
        return
