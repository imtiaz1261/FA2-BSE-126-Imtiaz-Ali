"""
services/subscription_service.py — Subscription Management
============================================================
Handles plan info, Stripe checkout, webhook processing, and
the plan limits used by the enforcement gate.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.core.logging import get_logger
from backend.db.models.subscription import (
    Subscription, SubscriptionPlan, SubscriptionStatus,
)
from backend.schemas.subscription import PlanLimits
from backend.services.usage_service import (
    get_plan_daily_requests, get_plan_doc_limit, get_plan_monthly_tokens,
)

logger = get_logger(__name__)


def get_plan_limits(plan_name: str) -> PlanLimits:
    """Return limit configuration for a given plan name."""
    plan = SubscriptionPlan(plan_name)
    return PlanLimits(
        plan=plan.value,
        monthly_tokens=get_plan_monthly_tokens(plan),
        daily_requests=get_plan_daily_requests(plan),
        max_document_uploads=get_plan_doc_limit(plan),
        max_file_size_mb=settings.MAX_UPLOAD_SIZE_MB,
        rag_enabled=True,
        agents_enabled=plan != SubscriptionPlan.FREE,
    )


ALL_PLANS = [
    get_plan_limits("free"),
    get_plan_limits("pro"),
    get_plan_limits("enterprise"),
]


async def get_subscription(db: AsyncSession, user_id: uuid.UUID) -> Subscription | None:
    result = await db.execute(
        select(Subscription).where(Subscription.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def create_checkout_session(plan: str, user_id: uuid.UUID) -> str:
    """
    Create a Stripe checkout session for plan upgrade.
    Returns the checkout URL.
    Falls back to a mock URL if Stripe keys are not configured.
    """
    if not settings.STRIPE_SECRET_KEY or settings.STRIPE_SECRET_KEY.startswith("sk_test_your"):
        # Mock URL for development
        return f"http://localhost:8000/api/v1/subscriptions/mock-checkout?plan={plan}&user={user_id}"

    try:
        import stripe
        stripe.api_key = settings.STRIPE_SECRET_KEY
        price_id = (
            settings.STRIPE_PRO_PRICE_ID
            if plan == "pro"
            else settings.STRIPE_ENTERPRISE_PRICE_ID
        )
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="subscription",
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=f"{settings.FRONTEND_URL}/?checkout=success",
            cancel_url=f"{settings.FRONTEND_URL}/?checkout=cancelled",
            metadata={"user_id": str(user_id), "plan": plan},
        )
        return session.url
    except Exception as exc:
        logger.error("stripe_checkout_failed", error=str(exc))
        raise


async def handle_webhook_upgrade(
    db: AsyncSession,
    user_id: uuid.UUID,
    plan: str,
    stripe_customer_id: str | None = None,
    stripe_subscription_id: str | None = None,
) -> Subscription:
    """Upgrade a user's subscription (called from webhook or mock)."""
    sub = await get_subscription(db, user_id)
    if not sub:
        sub = Subscription(user_id=user_id)
        db.add(sub)

    now = datetime.now(timezone.utc)
    sub.plan = SubscriptionPlan(plan)
    sub.status = SubscriptionStatus.ACTIVE
    sub.current_period_start = now
    sub.current_period_end = now + timedelta(days=30)
    if stripe_customer_id:
        sub.stripe_customer_id = stripe_customer_id
    if stripe_subscription_id:
        sub.stripe_subscription_id = stripe_subscription_id
    await db.flush()

    logger.info("subscription_upgraded", user_id=str(user_id), plan=plan)
    return sub


async def cancel_subscription(db: AsyncSession, user_id: uuid.UUID) -> None:
    sub = await get_subscription(db, user_id)
    if sub:
        sub.status = SubscriptionStatus.CANCELLED
        await db.flush()
        logger.info("subscription_cancelled", user_id=str(user_id))
