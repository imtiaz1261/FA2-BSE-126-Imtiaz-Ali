"""
db/models/usage.py — UsageRecord ORM Model
============================================
Logs every AI request with full token and cost details.

Table: usage_records

This table serves two purposes:
    1. Enforcement — the usage_service queries it to check whether
       a user has hit their plan limit for the current billing period.
    2. Analytics  — the admin dashboard aggregates it to show cost,
       token consumption, feature breakdown, and error rates.

One row is written after EVERY AI operation (chat, RAG query,
agent run, tool call) regardless of success or failure.
Writing on failure is deliberate — it proves the guardrails worked
and ensures we don't silently lose cost data on retried requests.
"""

import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum
from decimal import Decimal

from sqlalchemy import (
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
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db._base import Base


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class AIFeature(str, PyEnum):
    """
    The AI feature that generated this usage record.

    chat:        Standard conversational message to the LLM
    rag:         Retrieval-augmented generation (document Q&A)
    agent:       LangGraph agent orchestration run
    tool_call:   A single tool invocation within an agent run
    """
    CHAT = "chat"
    RAG = "rag"
    AGENT = "agent"
    TOOL_CALL = "tool_call"


class RequestStatus(str, PyEnum):
    """
    Outcome of the AI request.

    success:           LLM responded successfully
    error:             LLM or application error occurred
    blocked:           Blocked by subscription/usage limit (no LLM call made)
    guardrail_blocked: Blocked by input or output guardrail (no/partial LLM call)
    """
    SUCCESS = "success"
    ERROR = "error"
    BLOCKED = "blocked"
    GUARDRAIL_BLOCKED = "guardrail_blocked"


# ---------------------------------------------------------------------------
# ORM Model
# ---------------------------------------------------------------------------

class UsageRecord(Base):
    """
    One row per AI request.

    Written by usage_service.log_usage() immediately after every
    AI operation completes (or is blocked).

    Aggregation queries used by the enforcement gate:
        SELECT SUM(total_tokens)
        FROM usage_records
        WHERE user_id = :uid
          AND status = 'success'
          AND created_at >= :period_start
          AND created_at <= :period_end

        SELECT COUNT(*)
        FROM usage_records
        WHERE user_id = :uid
          AND feature = 'chat'
          AND created_at >= :period_start_today
    """

    __tablename__ = "usage_records"

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
    # Foreign Keys
    # ------------------------------------------------------------------
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="User who made the request",
    )

    # Nullable — RAG queries and agent runs may not belong to a conversation
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Conversation this request belongs to (if applicable)",
    )

    # ------------------------------------------------------------------
    # Request Classification
    # ------------------------------------------------------------------
    feature: Mapped[AIFeature] = mapped_column(
        Enum(AIFeature, name="aifeature", create_type=True,
             values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        index=True,
        comment="AI feature that generated this record",
    )

    status: Mapped[RequestStatus] = mapped_column(
        Enum(RequestStatus, name="requeststatus", create_type=True,
             values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=RequestStatus.SUCCESS,
        index=True,
        comment="Outcome of the AI request",
    )

    # ------------------------------------------------------------------
    # Token Counts
    # ------------------------------------------------------------------
    # Prompt tokens:     tokens in the input (system + history + user message)
    # Completion tokens: tokens in the LLM response
    # Total tokens:      prompt + completion (used for limit enforcement)

    prompt_tokens: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
        comment="Input tokens sent to the LLM",
    )

    completion_tokens: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
        comment="Output tokens received from the LLM",
    )

    total_tokens: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
        comment="Total tokens (prompt + completion)",
    )

    # ------------------------------------------------------------------
    # Cost Tracking
    # ------------------------------------------------------------------
    # Stored as NUMERIC(10,6) — supports up to $9999.999999
    # Precision to 6 decimal places because GPT-4o-mini costs fractions
    # of a cent per request.

    estimated_cost_usd: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=6),
        nullable=False,
        default=Decimal("0.000000"),
        server_default=text("0.000000"),
        comment="Estimated USD cost calculated from token counts and model pricing",
    )

    # ------------------------------------------------------------------
    # Request Metadata
    # ------------------------------------------------------------------
    model: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="",
        server_default=text("''"),
        comment="LLM model name used for this request (e.g. gpt-4o-mini)",
    )

    latency_ms: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
        comment="End-to-end request latency in milliseconds",
    )

    # Optional error message for failed requests
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default=None,
        comment="Error detail if status=error or status=guardrail_blocked",
    )

    # ------------------------------------------------------------------
    # Timestamp
    # ------------------------------------------------------------------
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
        index=True,
        comment="When this AI request was made (UTC)",
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------
    user: Mapped["User"] = relationship(  # noqa: F821
        "User",
        back_populates="usage_records",
    )

    conversation: Mapped["Conversation | None"] = relationship(  # noqa: F821
        "Conversation",
        back_populates="usage_records",
    )

    # ------------------------------------------------------------------
    # Indexes — designed around the two primary query patterns:
    #   1. Enforcement: SUM(tokens) for user in billing period
    #   2. Analytics:   GROUP BY feature, model, status, date
    # ------------------------------------------------------------------
    __table_args__ = (
        # Enforcement gate query: user + time window
        Index(
            "ix_usage_user_created",
            "user_id", "created_at",
        ),
        # Enforcement gate: user + feature + time (daily request limits)
        Index(
            "ix_usage_user_feature_created",
            "user_id", "feature", "created_at",
        ),
        # Admin analytics: aggregate by feature/status across all users
        Index(
            "ix_usage_feature_status_created",
            "feature", "status", "created_at",
        ),
        {
            "comment": "Per-request AI usage log for enforcement and billing analytics"
        },
    )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def __repr__(self) -> str:
        return (
            f"<UsageRecord id={self.id} user={self.user_id} "
            f"feature={self.feature.value} tokens={self.total_tokens} "
            f"status={self.status.value}>"
        )

    @property
    def was_successful(self) -> bool:
        return self.status == RequestStatus.SUCCESS

    @property
    def was_blocked(self) -> bool:
        return self.status in (
            RequestStatus.BLOCKED,
            RequestStatus.GUARDRAIL_BLOCKED,
        )
