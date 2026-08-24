"""
ai/llm.py — LLM & Embeddings Factory
======================================
Lazy factory functions so the OpenAI client is only constructed
when first needed, not at module import time.  This means tests
that don't touch the LLM can run without an API key.
"""

from __future__ import annotations
from functools import lru_cache

from backend.core.config import settings
from backend.core.logging import get_logger

logger = get_logger(__name__)


def get_llm(streaming: bool = False, temperature: float | None = None):
    """
    Return a configured ChatOpenAI instance.

    Args:
        streaming:   Enable token-by-token streaming callbacks.
        temperature: Override the default temperature from settings.
    """
    try:
        from langchain_openai import ChatOpenAI
    except ImportError:
        raise ImportError(
            "langchain-openai is not installed. "
            "Run: pip install langchain-openai"
        )

    # For Groq compatibility, we need to set api_version to the format it expects
    # Groq uses the OpenAI-compatible endpoint at api.groq.com
    return ChatOpenAI(
        model=settings.OPENAI_MODEL,
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_API_BASE,
        api_version="2024-11-20",  # Groq supports OpenAI's API format
        temperature=temperature if temperature is not None else settings.OPENAI_TEMPERATURE,
        max_tokens=settings.OPENAI_MAX_TOKENS,
        streaming=streaming,
    )


@lru_cache(maxsize=1)
def get_embeddings():
    """
    Return a cached OpenAIEmbeddings instance.
    Cached because the embeddings model doesn't change at runtime.
    """
    try:
        from langchain_openai import OpenAIEmbeddings
    except ImportError:
        raise ImportError("langchain-openai is not installed.")

    return OpenAIEmbeddings(
        model=settings.OPENAI_EMBEDDING_MODEL,
        api_key=settings.OPENAI_API_KEY,
    )


def count_tokens(text: str, model: str | None = None) -> int:
    """Estimate token count using tiktoken."""
    try:
        import tiktoken
        enc = tiktoken.encoding_for_model(model or settings.OPENAI_MODEL)
        return len(enc.encode(text))
    except Exception:
        # Fallback: rough estimate
        return len(text) // 4
