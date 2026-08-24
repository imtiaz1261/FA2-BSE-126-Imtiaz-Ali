"""
db/models/subscription.py — Subscription ORM Model
====================================================
Tracks each user's current subscription plan, billing status,
and the active billing period window.

Table: subscriptions

Key design principle:
    Subscription limits (token counts, request counts) are NOT
    stored in this table.  They live in settings (config.py) and
    are looked up by plan name at runtime.  This keeps the DB
    schema stable while allowing limit changes without migrations.

    What IS stored here:
    - Which plan the user is on
    - Whether the subscription is in good standing
    - The current billing period (for usage reset logic)
    - Stripe identifiers (for paid plans)
"""

import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db._base import Base


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class SubscriptionPlan(str, PyEnum):
    """
    Available subscription plans.

    The string values are used as keys into settings to look up limits:
        settings.FREE_PLAN_MONTHLY_TOKENS
        settings.PRO_PLAN_MONTHLY_TOKENS
        settings.ENTERPRISE_PLAN_MONTHLY_TOKENS
    """
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class SubscriptionStatus(str, PyEnum):
    """
    Subscription lifecycle status — mirrors Stripe's status vocabulary.

    active:     Subscription is in good standing, AI features enabled.
    trialing:   User is in a free trial period.
    past_due:   Payment failed; grace period before suspension.
    cancelled:  User cancelled; access until period_end.
    expired:    Period ended with no renewal; access revoked.
    """
    ACTIVE = "active"
    TRIALING = "trialing"
    PAST_DUE = "past_due"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


# ---------------------------------------------------------------------------
# ORM Model
# ---------------------------------------------------------------------------

class Subscription(Base):
    """
    One subscription row per user (one-to-one relationship).

    The subscription is created automatically when a user registers
    (defaulting to the FREE plan) by the auth service.

    Enforcement logic (in usage_service.py) checks:
        1. subscription.status == ACTIVE (or TRIALING)
        2. current usage < plan limit for this billing period
    """

    __tablename__ = "subscriptions"

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
    # Foreign Key — one subscription per user
    # ------------------------------------------------------------------
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,         # enforces one-to-one at the DB level
        index=True,
        comment="Owner of this subscription",
    )

    # ------------------------------------------------------------------
    # Plan & Status
    # ------------------------------------------------------------------
    plan: Mapped[SubscriptionPlan] = mapped_column(
        Enum(SubscriptionPlan, name="subscriptionplan", create_type=True,
             values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=SubscriptionPlan.FREE,
        server_default=SubscriptionPlan.FREE.value,
        comment="Current plan tier: free | pro | enterprise",
    )

    status: Mapped[SubscriptionStatus] = mapped_column(
        Enum(SubscriptionStatus, name="subscriptionstatus", create_type=True,
             values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=SubscriptionStatus.ACTIVE,
        server_default=SubscriptionStatus.ACTIVE.value,
        index=True,
        comment="Billing status — controls access to AI features",
    )

    # ------------------------------------------------------------------
    # Billing Period
    # ------------------------------------------------------------------
    # These define the window for usage aggregation.
    # At the start of each period, the usage_service resets counters.
    # For free plans, we set a rolling 30-day window.
    # For paid plans, Stripe webhook updates these on renewal.

    current_period_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
        comment="Start of current billing period (UTC)",
    )

    current_period_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        # Default: 30 days from now — set properly by seeder/Stripe webhook
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now() + interval '30 days'"),
        comment="End of current billing period (UTC)",
    )

    # ------------------------------------------------------------------
    # Stripe Integration (nullable — free plan has no Stripe subscription)
    # ------------------------------------------------------------------
    stripe_customer_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        unique=True,
        default=None,
        comment="Stripe customer ID (cus_...)",
    )

    stripe_subscription_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        unique=True,
        default=None,
        comment="Stripe subscription ID (sub_...)",
    )

    stripe_price_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        default=None,
        comment="Stripe price ID for the current plan (price_...)",
    )

    # ------------------------------------------------------------------
    # Timestamps
    # ------------------------------------------------------------------
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
    )

    # ------------------------------------------------------------------
    # Relationship back to User
    # ------------------------------------------------------------------
    user: Mapped["User"] = relationship(  # noqa: F821
        "User",
        back_populates="subscription",
    )

    # ------------------------------------------------------------------
    # Indexes
    # ------------------------------------------------------------------
    __table_args__ = (
        # Find all active subscribers on a given plan (admin analytics)
        Index("ix_subscriptions_plan_status", "plan", "status"),
        # Find subscriptions whose billing period just ended (renewal job)
        Index("ix_subscriptions_period_end", "current_period_end"),
        {
            "comment": "User subscription plans and billing state"
        },
    )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def __repr__(self) -> str:
        return (
            f"<Subscription user_id={self.user_id} "
            f"plan={self.plan.value} status={self.status.value}>"
        )

    @property
    def is_active(self) -> bool:
        """
        True if the subscription allows AI feature access.
        Both ACTIVE and TRIALING statuses permit usage.
        """
        return self.status in (
            SubscriptionStatus.ACTIVE,
            SubscriptionStatus.TRIALING,
        )

    @property
    def is_paid(self) -> bool:
        """True if the user is on a paid plan (pro or enterprise)."""
        return self.plan in (
            SubscriptionPlan.PRO,
            SubscriptionPlan.ENTERPRISE,
        )

    @property
    def days_remaining(self) -> int:
        """Days left in the current billing period."""
        now = datetime.now(timezone.utc)
        delta = self.current_period_end - now
        return max(0, delta.days)
