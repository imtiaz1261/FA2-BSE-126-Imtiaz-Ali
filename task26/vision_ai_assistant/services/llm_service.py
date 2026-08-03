"""LLM service abstraction for chat generation."""

from __future__ import annotations

import asyncio
from collections.abc import Iterator

from config.settings import AppSettings


class LLMService:
    """Encapsulates model calls behind a stable interface."""

    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings

    async def generate_response(self, user_text: str) -> str:
        """Generate assistant response for a safe user prompt.

        This Step 1 implementation is a placeholder. In Step 2 and Step 3,
        this method will call the configured provider with streaming support.
        """
        await asyncio.sleep(0)
        return (
            "LLM integration is not connected yet. "
            "Next step will wire secure request processing and streaming responses. "
            f"You asked: {user_text[:120]}"
        )

    def stream_chunks(self, text: str) -> Iterator[str]:
        """Yield a response string in small chunks suitable for Streamlit streaming."""
        words = text.split()
        for index, word in enumerate(words):
            suffix = " " if index < len(words) - 1 else ""
            yield f"{word}{suffix}"
