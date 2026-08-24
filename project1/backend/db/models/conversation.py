"""
db/models/conversation.py — Conversation & Message ORM Models
===============================================================
Two tables that together implement the full chat history system.

Tables:
    conversations  — named chat sessions owned by a user
    messages       — individual turns within a conversation

Relationship tree:
    User (1) ──→ (many) Conversation
    Conversation (1) ──→ (many) Message
    Conversation (1) ──→ (many) UsageRecord   [via conversation_id FK]

Loading strategy:
    conversations.messages uses lazy="noload" — messages are loaded
    explicitly when needed (e.g. GET /chat/{id}) not on every
    conversation list query.  This prevents N+1 query problems.
"""

import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db._base import Base


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class MessageRole(str, PyEnum):
    """
    The role of the message author — mirrors OpenAI's chat format.

    system:    System prompt / instructions (not shown to user)
    user:      Message from the human user
    assistant: Response from the AI assistant
    tool:      Output from a tool call (used in agent conversations)
    """
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


# ---------------------------------------------------------------------------
# Conversation Model
# ---------------------------------------------------------------------------

class Conversation(Base):
    """
    A named chat session belonging to a user.

    The conversation holds metadata only — the actual messages
    are in the messages table.  This keeps list queries fast.

    Users can:
    - Create new conversations
    - Rename conversations (update title)
    - Delete conversations (cascades to messages)
    - Search conversations by title (pg_trgm index)
    """

    __tablename__ = "conversations"

    # ------------------------------------------------------------------
    # Primary Key
    # ------------------------------------------------------------------
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )

    # ------------------------------------------------------------------
    # Foreign Key
    # ------------------------------------------------------------------
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Owner of this conversation",
    )

    # ------------------------------------------------------------------
    # Content
    # ------------------------------------------------------------------
    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        default="New Conversation",
        server_default=text("'New Conversation'"),
        comment="User-visible conversation title (auto-generated or renamed)",
    )

    # Tracks which AI feature generated the conversation
    # Allows filtering "show only my RAG conversations"
    feature: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="chat",
        server_default=text("'chat'"),
        comment="AI feature: chat | rag | agent",
    )

    # ------------------------------------------------------------------
    # Aggregated Stats (denormalised for fast display)
    # ------------------------------------------------------------------
    # These are updated by usage_service after each message.
    # Storing them here avoids COUNT queries on the messages table
    # just to render the conversation list sidebar.

    message_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
        comment="Total messages in this conversation",
    )

    total_tokens: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
        comment="Cumulative token count across all messages",
    )

    # ------------------------------------------------------------------
    # Timestamps
    # ------------------------------------------------------------------
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
        comment="When the conversation was created (UTC)",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
        comment="When the last message was added (UTC)",
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------
    user: Mapped["User"] = relationship(  # noqa: F821
        "User",
        back_populates="conversations",
    )

    messages: Mapped[list["Message"]] = relationship(
        "Message",
        back_populates="conversation",
        lazy="noload",
        cascade="all, delete-orphan",
        order_by="Message.created_at.asc()",
    )

    usage_records: Mapped[list["UsageRecord"]] = relationship(  # noqa: F821
        "UsageRecord",
        back_populates="conversation",
        lazy="noload",
    )

    # ------------------------------------------------------------------
    # Indexes
    # ------------------------------------------------------------------
    __table_args__ = (
        # List conversations for a user, newest first
        Index("ix_conversations_user_updated", "user_id", "updated_at"),
        {
            "comment": "Chat sessions — metadata container for messages"
        },
    )

    def __repr__(self) -> str:
        return (
            f"<Conversation id={self.id} user={self.user_id} "
            f"title={self.title!r}>"
        )


# ---------------------------------------------------------------------------
# Message Model
# ---------------------------------------------------------------------------

class Message(Base):
    """
    A single turn within a conversation.

    Every human message and AI response is a separate row.
    This makes it trivial to:
    - Replay the conversation history to the LLM
    - Show per-message token counts and costs
    - Export conversation transcripts
    - Delete individual messages (though we don't expose this in the API)

    The metadata_ JSONB column stores:
    - For assistant messages: {"sources": [...], "citations": [...]}
    - For tool messages:      {"tool_name": "...", "tool_input": {...}}
    - For guardrail blocks:   {"guardrail": "input", "reason": "..."}
    """

    __tablename__ = "messages"

    # ------------------------------------------------------------------
    # Primary Key
    # ------------------------------------------------------------------
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )

    # ------------------------------------------------------------------
    # Foreign Key
    # ------------------------------------------------------------------
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Conversation this message belongs to",
    )

    # ------------------------------------------------------------------
    # Message Content
    # ------------------------------------------------------------------
    role: Mapped[MessageRole] = mapped_column(
        Enum(MessageRole, name="messagerole", create_type=True,
             values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        comment="Message author: system | user | assistant | tool",
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="The full text content of the message",
    )

    # ------------------------------------------------------------------
    # Token & Cost Tracking
    # ------------------------------------------------------------------
    token_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
        comment="Token count for this individual message",
    )

    cost_usd: Mapped[float] = mapped_column(
        Numeric(precision=10, scale=6),
        nullable=False,
        default=0.0,
        server_default=text("0.000000"),
        comment="Estimated USD cost for generating this message",
    )

    # ------------------------------------------------------------------
    # Delivery Metadata
    # ------------------------------------------------------------------
    model: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        default=None,
        comment="LLM model that generated this message (assistant messages only)",
    )

    is_streaming: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
        comment="True if this response was delivered via SSE streaming",
    )

    # Flexible metadata stored as JSONB.
    # JSONB is indexed, compressed, and supports GIN indexes for
    # complex JSON queries — better than TEXT JSON storage.
    # Examples:
    #   {"sources": [{"doc": "report.pdf", "page": 4, "text": "..."}]}
    #   {"tool_name": "calculator", "tool_input": {"expr": "2+2"}}
    #   {"guardrail": "output", "reason": "PII detected"}
    metadata_: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata",         # actual DB column name (no underscore)
        JSONB,
        nullable=True,
        default=None,
        comment="Flexible JSON metadata: citations, tool calls, guardrail info",
    )

    # ------------------------------------------------------------------
    # Timestamp
    # ------------------------------------------------------------------
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
        comment="When this message was created (UTC)",
    )

    # ------------------------------------------------------------------
    # Relationship
    # ------------------------------------------------------------------
    conversation: Mapped[Conversation] = relationship(
        "Conversation",
        back_populates="messages",
    )

    # ------------------------------------------------------------------
    # Indexes
    # ------------------------------------------------------------------
    __table_args__ = (
        # Load all messages in a conversation ordered by time
        Index(
            "ix_messages_conversation_created",
            "conversation_id", "created_at",
        ),
        # Filter messages by role (e.g. get only user messages for analysis)
        Index(
            "ix_messages_conversation_role",
            "conversation_id", "role",
        ),
        {
            "comment": "Individual chat turns — user and assistant messages"
        },
    )

    def __repr__(self) -> str:
        preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return (
            f"<Message id={self.id} role={self.role.value} "
            f"tokens={self.token_count} content={preview!r}>"
        )

    @property
    def is_from_user(self) -> bool:
        return self.role == MessageRole.USER

    @property
    def is_from_assistant(self) -> bool:
        return self.role == MessageRole.ASSISTANT

    @property
    def citations(self) -> list[dict]:
        """Extract RAG citations from metadata if present."""
        if self.metadata_ and "sources" in self.metadata_:
            return self.metadata_["sources"]
        return []
