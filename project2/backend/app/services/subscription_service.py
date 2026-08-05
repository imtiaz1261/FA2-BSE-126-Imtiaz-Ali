"""
Subscription service — Phase 15.

Handles:
  • Plan limit definitions and quota enforcement
  • Monthly usage counting per user
  • Stripe test-mode checkout session creation and webhook processing
  • Plan upgrade / downgrade
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.usage import UsageRecord
from app.models.user import PlanTier, User

logger = logging.getLogger(__name__)

# ── Plan definitions ──────────────────────────────────────────────────────────

PLAN_LIMITS: Dict[str, Dict[str, Any]] = {
    PlanTier.FREE: {
        "monthly_requests": settings.FREE_PLAN_MONTHLY_LIMIT,    # 100
        "max_documents":    settings.FREE_PLAN_MAX_DOCS,          # 5
        "research_enabled": False,
        "agent_enabled":    False,
        "rag_enabled":      True,
        "price_usd":        0,
        "label":            "Free",
    },
    PlanTier.PRO: {
        "monthly_requests": settings.PRO_PLAN_MONTHLY_LIMIT,      # 2000
        "max_documents":    settings.PRO_PLAN_MAX_DOCS,            # 100
        "research_enabled": True,
        "agent_enabled":    True,
        "rag_enabled":      True,
        "price_usd":        19,
        "label":            "Pro",
    },
    PlanTier.ENTERPRISE: {
        "monthly_requests": settings.ENTERPRISE_PLAN_MONTHLY_LIMIT,  # 50000
        "max_documents":    settings.ENTERPRISE_PLAN_MAX_DOCS,        # 1000
        "research_enabled": True,
        "agent_enabled":    True,
        "rag_enabled":      True,
        "price_usd":        99,
        "label":            "Enterprise",
    },
}


def get_plan_limits(plan: PlanTier) -> Dict[str, Any]:
    return PLAN_LIMITS.get(plan, PLAN_LIMITS[PlanTier.FREE])


# ── Usage counting ────────────────────────────────────────────────────────────

def get_monthly_usage_count(db: Session, user_id: uuid.UUID) -> int:
    """Count LLM calls made by the user in the current calendar month."""
    now    = datetime.now(tz=timezone.utc)
    start  = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    result = db.scalar(
        select(func.count(UsageRecord.id))
        .where(UsageRecord.user_id == user_id)
        .where(UsageRecord.created_at >= start)
    )
    return int(result or 0)


def get_monthly_usage_detail(db: Session, user_id: uuid.UUID) -> Dict[str, Any]:
    """Return full usage stats for the current month."""
    now   = datetime.now(tz=timezone.utc)
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    calls = db.scalar(
        select(func.count(UsageRecord.id))
        .where(UsageRecord.user_id == user_id)
        .where(UsageRecord.created_at >= start)
    ) or 0
    tokens = db.scalar(
        select(func.sum(UsageRecord.tokens_used))
        .where(UsageRecord.user_id == user_id)
        .where(UsageRecord.created_at >= start)
    ) or 0
    cost = db.scalar(
        select(func.sum(UsageRecord.cost_usd))
        .where(UsageRecord.user_id == user_id)
        .where(UsageRecord.created_at >= start)
    ) or 0.0

    return {
        "calls":         int(calls),
        "tokens_used":   int(tokens),
        "cost_usd":      round(float(cost), 6),
        "period_start":  start.isoformat(),
        "period_end":    (start + timedelta(days=32)).replace(day=1).isoformat(),
    }


# ── Quota enforcement ─────────────────────────────────────────────────────────

def check_quota(db: Session, user: User) -> Tuple[bool, str]:
    """
    Returns (allowed, message).
    allowed=True  → request may proceed
    allowed=False → return 429 to client with message
    """
    limits = get_plan_limits(user.plan)
    monthly_limit = limits["monthly_requests"]

    used = get_monthly_usage_count(db, user.id)
    if used >= monthly_limit:
        plan_label = limits["label"]
        return False, (
            f"Monthly usage limit reached. "
            f"You have used {used}/{monthly_limit} requests on the {plan_label} plan. "
            f"Upgrade your subscription to continue."
        )
    return True, ""


def check_feature_access(user: User, feature: str) -> Tuple[bool, str]:
    """
    Check whether the user's plan includes a feature.
    feature: "research" | "agent" | "rag"
    """
    limits = get_plan_limits(user.plan)
    key    = f"{feature}_enabled"
    if not limits.get(key, False):
        plan_label = limits["label"]
        return False, (
            f"The {feature.title()} feature is not available on the {plan_label} plan. "
            f"Upgrade to Pro or Enterprise to unlock it."
        )
    return True, ""


# ── Stripe integration (test mode) ───────────────────────────────────────────

def create_stripe_checkout(
    user: User,
    target_plan: str,
) -> Optional[str]:
    """
    Create a Stripe Checkout session URL for upgrading.
    Returns the session URL or None when Stripe is not configured.
    """
    if not settings.STRIPE_SECRET_KEY:
        logger.info("Stripe not configured — skipping checkout creation.")
        return None

    plan_price_map = {
        "pro":        settings.STRIPE_PRO_PRICE_ID,
        "enterprise": settings.STRIPE_ENTERPRISE_PRICE_ID,
    }
    price_id = plan_price_map.get(target_plan.lower())
    if not price_id:
        return None

    try:
        import stripe
        stripe.api_key = settings.STRIPE_SECRET_KEY

        # Create or retrieve Stripe customer
        customer_id = user.stripe_customer_id
        if not customer_id:
            customer    = stripe.Customer.create(email=user.email, name=user.full_name or "")
            customer_id = customer.id

        session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=["card"],
            line_items=[{"price": price_id, "quantity": 1}],
            mode="subscription",
            success_url="http://localhost:8501?checkout=success",
            cancel_url="http://localhost:8501?checkout=cancelled",
            metadata={"user_id": str(user.id), "plan": target_plan},
        )
        return session.url
    except Exception as exc:
        logger.error("Stripe checkout creation failed: %s", exc)
        return None


def handle_stripe_webhook(
    db: Session,
    payload: bytes,
    sig_header: str,
) -> Dict[str, Any]:
    """Process incoming Stripe webhook (checkout.session.completed)."""
    if not settings.STRIPE_SECRET_KEY or not settings.STRIPE_WEBHOOK_SECRET:
        return {"status": "stripe_not_configured"}

    try:
        import stripe
        stripe.api_key = settings.STRIPE_SECRET_KEY

        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except Exception as exc:
        logger.error("Stripe webhook verification failed: %s", exc)
        return {"status": "invalid_signature"}

    if event["type"] == "checkout.session.completed":
        session  = event["data"]["object"]
        metadata = session.get("metadata", {})
        user_id  = metadata.get("user_id")
        plan     = metadata.get("plan", "pro")

        if user_id:
            try:
                uid  = uuid.UUID(user_id)
                user = db.get(User, uid)
                if user:
                    user.plan                   = PlanTier(plan)
                    user.stripe_customer_id      = session.get("customer")
                    user.stripe_subscription_id  = session.get("subscription")
                    user.plan_expires_at         = datetime.now(tz=timezone.utc) + timedelta(days=30)
                    db.commit()
                    logger.info("Upgraded user %s to plan=%s", user_id, plan)
            except Exception as exc:
                logger.error("Failed to update user plan from webhook: %s", exc)

    return {"status": "processed"}


def upgrade_plan_manual(
    db: Session,
    user: User,
    new_plan: str,
) -> User:
    """
    Directly upgrade a user's plan (for test/demo use when Stripe is not wired).
    In production this should only be called from the Stripe webhook handler.
    """
    try:
        plan_enum = PlanTier(new_plan.lower())
    except ValueError:
        raise ValueError(f"Unknown plan: {new_plan}")

    user.plan            = plan_enum
    user.plan_expires_at = datetime.now(tz=timezone.utc) + timedelta(days=30)
    db.commit()
    db.refresh(user)
    logger.info("Manual plan upgrade: user=%s → plan=%s", user.id, plan_enum)
    return user
