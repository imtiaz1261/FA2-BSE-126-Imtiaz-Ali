"""
Billing & Subscription models.

Tables:
- subscriptions              User subscription state (links to Stripe)
- stripe_webhook_events      Idempotent webhook processing
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class SubscriptionPlan(str, enum.Enum):
    """Available subscription plans."""
    free = "free"
    plus = "plus"
    pro = "pro"


class SubscriptionStatus(str, enum.Enum):
    """Stripe subscription statuses."""
    active = "active"
    trialing = "trialing"
    past_due = "past_due"
    canceled = "canceled"
    unpaid = "unpaid"
    incomplete = "incomplete"
    incomplete_expired = "incomplete_expired"


class Subscription(Base):
    """User subscription linked to Stripe."""

    __tablename__ = "subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False, unique=True
    )

    # Stripe IDs (null for free users)
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), index=True, nullable=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(255), index=True, nullable=True)
    stripe_price_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Plan & Status
    plan: Mapped[SubscriptionPlan] = mapped_column(
        Enum(SubscriptionPlan, name="subscription_plan"),
        default=SubscriptionPlan.free,
        nullable=False,
        index=True,
    )
    status: Mapped[SubscriptionStatus] = mapped_column(
        Enum(SubscriptionStatus, name="subscription_status"),
        default=SubscriptionStatus.active,
        nullable=False,
    )

    # Billing period
    current_period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Cancellation
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    canceled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    user: Mapped["User"] = relationship()

    __table_args__ = (
        Index("ix_subscriptions_status", "status"),
    )


class StripeWebhookEvent(Base):
    """Idempotent webhook event tracking."""

    __tablename__ = "stripe_webhook_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    stripe_event_id: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)

    # Event details
    processed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_stripe_webhook_events_event_type", "event_type"),
    )
