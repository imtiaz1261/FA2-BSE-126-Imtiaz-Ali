"""
DocumentChunk model — a single text chunk from a processed document.

Each chunk stores:
  - The source document and user it belongs to
  - Its page / position metadata
  - The raw chunk text (for BM25 / display)
  - A pgvector embedding column (Phase 9: dense retrieval)
  - A tsvector column for full-text search (Phase 10: hybrid BM25)
"""

import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Integer,
    Text,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.config import settings
from app.db.base_class import Base


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # --- Content ---
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # --- Metadata ---
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    page_number: Mapped[int] = mapped_column(Integer, nullable=True)
    char_start: Mapped[int] = mapped_column(BigInteger, nullable=True)
    char_end: Mapped[int] = mapped_column(BigInteger, nullable=True)

    # --- Dense vector (pgvector) ---
    embedding: Mapped[list] = mapped_column(
        Vector(settings.VECTOR_DIM), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # --- Relationships ---
    document: Mapped["Document"] = relationship(back_populates="chunks")  # type: ignore[name-defined]

    # --- Indexes (created in the migration) ---
    __table_args__ = (
        # cosine similarity HNSW index — created in migration with CREATE INDEX CONCURRENTLY
        # Index("ix_document_chunks_embedding", "embedding", postgresql_using="hnsw",
        #       postgresql_with={"m": 16, "ef_construction": 64},
        #       postgresql_ops={"embedding": "vector_cosine_ops"}),
    )
