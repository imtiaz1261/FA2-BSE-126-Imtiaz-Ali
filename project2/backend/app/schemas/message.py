"""Pydantic schemas for messages — Phase 6 + Phase 9/10 (citations)."""

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.models.message import MessageRole
from app.schemas.document import CitationOut


class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=8000)
    mode: str = Field(default="Chat")


class MessageOut(BaseModel):
    id: uuid.UUID
    role: MessageRole
    content: str
    created_at: datetime
    citations: Optional[List[CitationOut]] = None  # Phase 10 — populated for RAG replies

    model_config = {"from_attributes": True}
