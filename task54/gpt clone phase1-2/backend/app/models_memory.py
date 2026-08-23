"""
Memory & Personalization models.

Tables:
- user_memory_items      Durable facts about user (preferences, profile info, roles)
- memory_extraction_log  Audit trail of extraction events (per conversation)
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID, JSON as PGJSON
from pgvector.sqlalchemy import Vector
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class MemoryCategory(str, enum.Enum):
    """Classification of memory items for better retrieval and organization."""
    personal_info = "personal_info"           # Name, role, location
    preferences = "preferences"               # Work style, communication style
    goals_and_values = "goals_and_values"    # Career goals, values, priorities
    skills_and_expertise = "skills_and_expertise"  # Technical skills, domain knowledge
    constraints = "constraints"               # Time zones, availability, limitations
    recurring_tasks = "recurring_tasks"       # Repeated patterns, workflows
    project_context = "project_context"       # Current projects, ongoing work
    other = "other"


class UserMemoryItem(Base):
    """Individual fact stored about a user for long-term personalization."""

    __tablename__ = "user_memory_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )

    # The actual fact/preference stored
    fact: Mapped[str] = mapped_column(Text, nullable=False)

    # Category for semantic grouping (helps UI and retrieval)
    category: Mapped[MemoryCategory] = mapped_column(
        Enum(MemoryCategory, name="memory_category"),
        default=MemoryCategory.other,
        nullable=False,
    )

    # Semantic embedding (1536-dim for OpenAI embeddings, configurable)
    embedding: Mapped[list | None] = mapped_column(Vector(1536), nullable=True)

    # Denormalized for relevance scoring in retrieval
    relevance_score: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)

    # Track source for audit trail
    source_conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True, index=True
    )
    source_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    extraction_context: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # Snippet from conversation that led to this memory

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    user_edited_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )  # When user manually edited this

    # Is this memory actively used in context injection?
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Access tracking for LRU eviction if memory store gets large
    last_retrieved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    retrieval_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    __table_args__ = (
        Index("ix_user_memory_items_category", "category"),
        Index("ix_user_memory_items_is_active", "is_active"),
        Index("ix_user_memory_items_relevance", "relevance_score"),
    )


class MemoryExtractionLog(Base):
    """Audit log of extraction events (when facts were extracted from conversations)."""

    __tablename__ = "memory_extraction_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )

    # Source: which conversation triggered extraction
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True
    )

    # How many facts were extracted in this event?
    facts_extracted_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Facts that were identified but NOT stored (e.g., duplicates, sensitive data)
    facts_rejected_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Rejection reasons (JSON list of strings for transparency)
    rejection_reasons: Mapped[list] = mapped_column(
        PGJSON, default=list, nullable=False
    )

    # LLM prompt tokens used (for tracking usage/cost)
    llm_prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    llm_completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Trigger: "manual" (user requested), "post_conversation" (after chat ended), "periodic" (scheduled)
    trigger: Mapped[str] = mapped_column(String(50), default="post_conversation", nullable=False)

    # Success status
    success: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_extraction_logs_user_id", "user_id"),
        Index("ix_extraction_logs_conversation_id", "conversation_id"),
        Index("ix_extraction_logs_trigger", "trigger"),
    )


class UserMemorySettings(Base):
    """User's memory module preferences (enable/disable, retention policy)."""

    __tablename__ = "user_memory_settings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True, nullable=False
    )

    # Master toggle: is memory enabled for this user?
    memory_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Should facts auto-extract from conversations?
    auto_extract_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Max memory items before oldest (by retrieval_count) gets evicted
    max_memory_items: Mapped[int] = mapped_column(Integer, default=100, nullable=False)

    # How many top memory items to inject at start of each conversation?
    context_injection_count: Mapped[int] = mapped_column(Integer, default=5, nullable=False)

    # Similarity threshold (0-1) for retrieving relevant memories
    retrieval_threshold: Mapped[float] = mapped_column(Float, default=0.6, nullable=False)

    # Data retention: how many days to keep extracted facts (0 = keep forever)
    retention_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Last time extraction was run (for periodic job)
    last_extraction_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Created/updated timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (Index("ix_memory_settings_user_id", "user_id"),)


class MemoryRetrievalLog(Base):
    """Track when memories are retrieved and injected into conversations (for analytics)."""

    __tablename__ = "memory_retrieval_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )

    # Which conversation was this retrieval for?
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True
    )

    # Which memory items were retrieved?
    retrieved_memory_ids: Mapped[list] = mapped_column(PGJSON, default=list, nullable=False)

    # User's opening message that triggered retrieval
    user_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # How similar was the best match? (0-1)
    max_similarity_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_retrieval_logs_user_id", "user_id"),
        Index("ix_retrieval_logs_conversation_id", "conversation_id"),
    )
