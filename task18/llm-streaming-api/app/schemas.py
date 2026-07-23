"""Request/response schemas."""

from typing import Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class ChatStreamRequest(BaseModel):
    """Body for POST /chat/stream."""

    messages: list[ChatMessage] = Field(
        ..., min_length=1, description="Conversation so far, oldest first."
    )
    model: str | None = Field(
        default=None, description="Override the default model for this request."
    )
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=1024, ge=1, le=8192)
    request_id: str | None = Field(
        default=None, description="Client-supplied id; also usable to cancel this stream."
    )
