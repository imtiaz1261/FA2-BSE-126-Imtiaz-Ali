"""
Admin system models.

Tables:
- admin_audit_logs      audit log of all admin actions
- moderation_flags      flagged conversations for content review
- model_request_logs    performance metrics for LLM model requests
- daily_platform_metrics   aggregated daily platform statistics
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ModerationFlag(Base):
    """Flagged conversation for content moderation review."""

    __tablename__ = "moderation_flags"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
    )
    message_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("messages.id", ondelete="SET NULL"), nullable=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    category: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="pending", index=True
    )
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    metadata_json: Mapped[dict] = mapped_column(
        "metadata",
        JSON,
        default=dict,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    __table_args__ = (
        Index("ix_moderation_flags_conversation_id", "conversation_id"),
    )


class AdminAuditLog(Base):
    """Audit log of all admin actions."""

    __tablename__ = "admin_audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    admin_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    target_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict] = mapped_column(
        "metadata",
        JSON,
        default=dict,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    __table_args__ = (
    )


class ModelRequestLog(Base):
    """Performance metrics for LLM model requests."""

    __tablename__ = "model_request_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True
    )

    model: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    estimated_cost: Mapped[float] = mapped_column(Numeric(12, 6), nullable=False, default=0)

    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    __table_args__ = (
    )


class DailyPlatformMetric(Base):
    """Aggregated daily platform statistics."""

    __tablename__ = "daily_platform_metrics"

    date: Mapped[datetime] = mapped_column(Date, primary_key=True)

    dau: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    messages: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    input_tokens: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    output_tokens: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    estimated_cost: Mapped[float] = mapped_column(Numeric(14, 4), nullable=False, default=0)

    new_users: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    paid_users: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (Index("ix_daily_platform_metrics_date", "date"),)
