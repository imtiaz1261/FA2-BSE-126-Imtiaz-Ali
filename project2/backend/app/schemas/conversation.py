"""Pydantic schemas for conversations."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ConversationCreate(BaseModel):
    title: str = Field(default="New Conversation", max_length=255)


class ConversationUpdate(BaseModel):
    title: str = Field(max_length=255)


class ConversationOut(BaseModel):
    id: uuid.UUID
    title: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
