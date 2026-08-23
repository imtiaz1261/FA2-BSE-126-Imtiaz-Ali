"""
Schemas for RAG (Document Q&A) module.

Includes request/response schemas for:
- Document upload
- Upload job status polling
- Document management (list, delete)
- Retrieval results with citations
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ============================================================================
# Upload Request/Response
# ============================================================================


class DocumentUploadRequest(BaseModel):
    """Upload a document for RAG indexing."""

    conversation_id: Optional[UUID] = Field(
        None, description="Optional: scope to a specific conversation"
    )


class UploadJobResponse(BaseModel):
    """Response with upload job status for polling."""

    job_id: UUID = Field(description="Job ID for polling status")
    document_id: Optional[UUID] = Field(description="Document ID once created")
    status: str = Field(
        description="pending -> processing -> ready (or failed)"
    )
    progress: int = Field(default=0, description="0-100 progress percentage")
    error_message: Optional[str] = Field(None, description="Error details if failed")

    class Config:
        from_attributes = True


# ============================================================================
# Document Management
# ============================================================================


class DocumentMetadata(BaseModel):
    """Metadata for a document."""

    id: UUID
    filename: str
    file_type: str  # pdf, docx, txt, csv
    file_size_bytes: int
    status: str  # pending, processing, ready, failed
    chunk_count: int
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    """List of documents for a conversation."""

    documents: list[DocumentMetadata]
    total_count: int


class DocumentDeleteRequest(BaseModel):
    """Delete a document."""

    document_id: UUID


# ============================================================================
# Retrieval & Citations
# ============================================================================


class RetrievedChunk(BaseModel):
    """A chunk retrieved during RAG retrieval."""

    chunk_id: UUID
    document_id: UUID
    filename: str
    page_number: Optional[int] = Field(None, description="Page number if applicable")
    chunk_index: int
    text: str
    relevance_score: float = Field(
        description="Hybrid score (0-1): weighted BM25 + vector similarity"
    )


class RetrievalResult(BaseModel):
    """Retrieval results for a query."""

    query: str
    chunks: list[RetrievedChunk] = Field(description="Top-k retrieved chunks")
    total_chunks_searched: int = Field(
        description="Total chunks searched in conversation scope"
    )


class CitationMetadata(BaseModel):
    """Citation for a retrieved chunk used in the response."""

    chunk_id: UUID
    document_id: UUID
    filename: str
    page_number: Optional[int] = None
    chunk_index: int


class ChatMessageWithCitations(BaseModel):
    """Assistant message with citations for retrieved sources."""

    role: str = "assistant"
    content: str = Field(description="Generated response")
    citations: list[CitationMetadata] = Field(
        default_factory=list, description="Sources used in response"
    )


# ============================================================================
# File Upload Status Polling
# ============================================================================


class UploadStatusRequest(BaseModel):
    """Poll for upload job status."""

    job_id: UUID


class UploadStatusResponse(BaseModel):
    """Upload job status."""

    job_id: UUID
    document_id: Optional[UUID] = None
    status: str  # pending, processing, ready, failed
    progress: int = Field(ge=0, le=100)
    chunk_count: int = 0
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
