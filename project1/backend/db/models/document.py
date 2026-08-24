"""
db/models/document.py — Document ORM Model
============================================
Tracks every uploaded document and its processing state through
the RAG ingestion pipeline.

Table: documents

Pipeline states:
    pending     → File saved to disk, queued for processing
    processing  → Background task is chunking and embedding
    ready       → Embeddings stored in vector DB, queryable
    failed      → Processing error (see error_message)

Storage architecture:
    - Binary file:  UPLOAD_DIR/{user_id}/{document_id}/{filename}
    - Metadata:     This table
    - Embeddings:   Vector store (ChromaDB or pgvector)
                    Collection name = user_{user_id} (per-user isolation)

The document_id is used as the namespace in the vector store
so embeddings can be deleted when a document is removed.
"""

import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db._base import Base


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class DocumentStatus(str, PyEnum):
    """
    Processing pipeline status for an uploaded document.

    pending:    File received, waiting for background processing
    processing: Background task is actively chunking and embedding
    ready:      Embeddings generated and stored — document is queryable
    failed:     Processing failed (error_message contains details)
    """
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class DocumentType(str, PyEnum):
    """
    Supported document types.
    Determines which loader is used during processing.

    pdf:   pypdf loader
    docx:  python-docx loader
    txt:   plain text loader
    md:    markdown text loader
    csv:   CSV loader (each row as a chunk)
    """
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"
    MD = "md"
    CSV = "csv"


# ---------------------------------------------------------------------------
# ORM Model
# ---------------------------------------------------------------------------

class Document(Base):
    """
    Metadata record for an uploaded document.

    One row is created when the file is uploaded.
    The status field is updated as processing progresses.
    The row is deleted when the user deletes the document —
    the cascade also triggers cleanup of vector store embeddings
    (handled in document_service.delete_document).
    """

    __tablename__ = "documents"

    # ------------------------------------------------------------------
    # Primary Key
    # ------------------------------------------------------------------
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
        comment="Unique document ID — also used as vector store namespace",
    )

    # ------------------------------------------------------------------
    # Foreign Key
    # ------------------------------------------------------------------
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="User who uploaded this document",
    )

    # ------------------------------------------------------------------
    # File Identity
    # ------------------------------------------------------------------
    filename: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Original filename as uploaded by the user",
    )

    file_path: Mapped[str] = mapped_column(
        String(1000),
        nullable=False,
        comment="Absolute path to the file on disk",
    )

    file_size_bytes: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
        server_default=text("0"),
        comment="File size in bytes",
    )

    mime_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="application/octet-stream",
        comment="MIME type detected at upload time",
    )

    document_type: Mapped[DocumentType] = mapped_column(
        Enum(DocumentType, name="documenttype", create_type=True,
             values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        comment="File type — determines which loader is used",
    )

    # SHA-256 hash of the file content
    # Used for deduplication: if hash already exists for this user,
    # skip re-uploading and re-processing.
    file_hash: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        default=None,
        comment="SHA-256 hex digest of the file content (deduplication key)",
    )

    # ------------------------------------------------------------------
    # Processing Pipeline State
    # ------------------------------------------------------------------
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus, name="documentstatus", create_type=True,
             values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=DocumentStatus.PENDING,
        server_default=DocumentStatus.PENDING.value,
        index=True,
        comment="Current pipeline stage",
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default=None,
        comment="Error detail if status=failed",
    )

    # ------------------------------------------------------------------
    # Processing Results
    # ------------------------------------------------------------------
    # Populated when status transitions to READY

    chunk_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
        comment="Number of text chunks generated from this document",
    )

    page_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
        comment="Number of pages (for PDFs) or 0 for other types",
    )

    embedding_model: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        default=None,
        comment="Embedding model used (e.g. text-embedding-3-small)",
    )

    # ------------------------------------------------------------------
    # Vector Store Reference
    # ------------------------------------------------------------------
    # Each user has their own collection in the vector store.
    # Pattern: "user_{user_id_hex}"
    # This enforces strict per-user document isolation.
    collection_name: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        default=None,
        comment="Vector store collection name for this user's documents",
    )

    # ------------------------------------------------------------------
    # Timestamps
    # ------------------------------------------------------------------
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
        comment="Upload timestamp (UTC)",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
        comment="Last status update timestamp (UTC)",
    )

    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        comment="When processing completed successfully (UTC)",
    )

    # ------------------------------------------------------------------
    # Relationship
    # ------------------------------------------------------------------
    user: Mapped["User"] = relationship(  # noqa: F821
        "User",
        back_populates="documents",
    )

    # ------------------------------------------------------------------
    # Indexes
    # ------------------------------------------------------------------
    __table_args__ = (
        # List user's documents with status filter
        Index("ix_documents_user_status", "user_id", "status"),
        # Deduplication check: user + hash
        Index("ix_documents_user_hash", "user_id", "file_hash"),
        # Admin: find all failed documents for retry
        Index("ix_documents_status_created", "status", "created_at"),
        {
            "comment": "Uploaded documents and their RAG processing state"
        },
    )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def __repr__(self) -> str:
        return (
            f"<Document id={self.id} filename={self.filename!r} "
            f"status={self.status.value} chunks={self.chunk_count}>"
        )

    @property
    def is_ready(self) -> bool:
        """True if the document is fully processed and queryable."""
        return self.status == DocumentStatus.READY

    @property
    def is_processing(self) -> bool:
        return self.status in (
            DocumentStatus.PENDING,
            DocumentStatus.PROCESSING,
        )

    @property
    def file_size_mb(self) -> float:
        """File size in megabytes, rounded to 2 decimal places."""
        return round(self.file_size_bytes / (1024 * 1024), 2)
