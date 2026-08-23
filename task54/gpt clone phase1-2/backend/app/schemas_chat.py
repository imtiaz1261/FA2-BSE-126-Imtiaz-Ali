"""Pydantic schemas for /chat/* endpoints."""
from typing import Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=32_000)


class ChatStreamRequest(BaseModel):
    """The full message history for the conversation so far, oldest first.
    The last entry should be the new user message being responded to.
    """

    conversation_id: str | None = None
    messages: list[ChatMessage] = Field(min_length=1)


class StopGenerationResponse(BaseModel):
    message: str
    stopped: bool
