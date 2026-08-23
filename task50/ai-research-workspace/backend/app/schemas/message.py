"""Pydantic schemas for messages."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.message import MessageRole


class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=8000)
    mode: str = Field(default="Chat")


class MessageOut(BaseModel):
    id: uuid.UUID
    role: MessageRole
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}
