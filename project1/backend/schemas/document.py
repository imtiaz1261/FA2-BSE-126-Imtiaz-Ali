"""schemas/document.py — Document upload/query request/response models."""
import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class DocumentResponse(BaseModel):
    id: uuid.UUID
    filename: str
    file_size_bytes: int
    document_type: str
    status: str
    chunk_count: int
    page_count: int
    embedding_model: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    processed_at: Optional[datetime] = None
    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    documents: list[DocumentResponse]
    total: int


class RAGQueryRequest(BaseModel):
    question: str
    document_ids: Optional[list[uuid.UUID]] = None   # None = search all user docs
    top_k: int = 5
    mode: str = "hybrid"    # vector | keyword | hybrid

    @classmethod
    def validate_question(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Question cannot be empty")
        return v


class CitationSource(BaseModel):
    document_id: str
    filename: str
    page: Optional[int] = None
    chunk_text: str
    score: float


class RAGQueryResponse(BaseModel):
    question: str
    answer: str
    sources: list[CitationSource]
    tokens_used: int
    model: str


class DocumentStatusResponse(BaseModel):
    id: uuid.UUID
    filename: str
    status: str
    chunk_count: int
    error_message: Optional[str] = None
