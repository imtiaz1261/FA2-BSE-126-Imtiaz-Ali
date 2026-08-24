"""schemas/chat.py — Chat request/response models."""
import uuid
from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, field_validator


class ConversationCreate(BaseModel):
    title: str = "New Conversation"
    feature: str = "chat"


class ConversationRename(BaseModel):
    title: str

    @field_validator("title")
    @classmethod
    def not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Title cannot be empty")
        return v[:200]


class ConversationResponse(BaseModel):
    id: uuid.UUID
    title: str
    feature: str
    message_count: int
    total_tokens: int
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


class MessageResponse(BaseModel):
    id: uuid.UUID
    conversation_id: uuid.UUID
    role: str
    content: str
    token_count: int
    model: Optional[str] = None
    metadata_: Optional[dict[str, Any]] = None
    created_at: datetime
    model_config = {"from_attributes": True}


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[uuid.UUID] = None
    mode: str = "chat"          # chat | rag | agent
    stream: bool = True

    @field_validator("message")
    @classmethod
    def message_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Message cannot be empty")
        if len(v) > 32_000:
            raise ValueError("Message exceeds maximum length")
        return v

    @field_validator("mode")
    @classmethod
    def valid_mode(cls, v: str) -> str:
        if v not in ("chat", "rag", "agent"):
            raise ValueError("mode must be chat, rag, or agent")
        return v


class ChatResponse(BaseModel):
    conversation_id: uuid.UUID
    message_id: uuid.UUID
    role: str = "assistant"
    content: str
    tokens_used: int
    model: str
    citations: list[dict] = []


class ConversationListResponse(BaseModel):
    conversations: list[ConversationResponse]
    total: int


class MessageListResponse(BaseModel):
    messages: list[MessageResponse]
    conversation_id: uuid.UUID
