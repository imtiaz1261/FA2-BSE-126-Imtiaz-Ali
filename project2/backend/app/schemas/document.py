"""Pydantic schemas for documents — Phase 8 + Phase 9/10."""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models.document import DocumentStatus


class DocumentOut(BaseModel):
    id: uuid.UUID
    filename: str
    content_type: str
    size_bytes: int
    status: DocumentStatus
    created_at: datetime

    model_config = {"from_attributes": True}


class CitationOut(BaseModel):
    """A single citation extracted from a RAG reply — Phase 10."""

    ref: str           # e.g. "[Doc 1]"
    document_name: str
    page_number: Optional[int] = None
    score: float
    snippet: str       # first ~200 chars of the source chunk
