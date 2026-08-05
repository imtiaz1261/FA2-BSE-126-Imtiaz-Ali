"""
Subscription router — Phase 15.

GET  /subscription/me          — current plan, quota, next renewal
POST /subscription/upgrade     — manual upgrade (demo) or Stripe checkout
POST /subscription/webhook     — Stripe webhook receiver
GET  /usage/me                 — detailed monthly usage for the current user
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User

logger = logging.getLogger(__name__)

# Two routers — subscription management and personal usage dashboard
subscription_router = APIRouter(prefix="/subscription", tags=["subscription"])
usage_router        = APIRouter(prefix="/usage",        tags=["usage"])


# ── schemas ────────────────────────────────────────────────────────────────────

class UpgradeRequest(BaseModel):
    plan: str                   # "pro" | "enterprise"
    use_stripe: bool = False    # True → return Stripe checkout URL


# ── GET /subscription/me ───────────────────────────────────────────────────────

@subscription_router.get("/me")
def get_my_subscription(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Return the user's current plan, limits, and this-month usage."""
    from app.services.subscription_service import (
        get_monthly_usage_count,
        get_plan_limits,
    )

    limits = get_plan_limits(current_user.plan)
    used   = get_monthly_usage_count(db, current_user.id)

    return {
        "plan":              current_user.plan.value,
        "plan_label":        limits["label"],
        "monthly_limit":     limits["monthly_requests"],
        "monthly_used":      used,
        "monthly_remaining": max(0, limits["monthly_requests"] - used),
        "max_documents":     limits["max_documents"],
        "research_enabled":  limits["research_enabled"],
        "agent_enabled":     limits["agent_enabled"],
        "rag_enabled":       limits["rag_enabled"],
        "price_usd":         limits["price_usd"],
        "stripe_customer_id": current_user.stripe_customer_id,
        "plan_expires_at":   current_user.plan_expires_at.isoformat()
                             if current_user.plan_expires_at else None,
    }


# ── POST /subscription/upgrade ────────────────────────────────────────────────

@subscription_router.post("/upgrade")
async def upgrade_subscription(
    data: UpgradeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Upgrade the user's plan.
    • If use_stripe=True and STRIPE_SECRET_KEY is set → return Stripe checkout URL.
    • Otherwise → direct (test-mode) upgrade without payment.
    """
    from app.services.subscription_service import (
        create_stripe_checkout,
        upgrade_plan_manual,
    )

    valid_plans = {"pro", "enterprise"}
    if data.plan.lower() not in valid_plans:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid plan '{data.plan}'. Choose: {valid_plans}",
        )

    if data.use_stripe:
        url = create_stripe_checkout(current_user, data.plan)
        if url:
            return {"checkout_url": url, "plan": data.plan}
        # Fall through to manual if Stripe not configured

    # Direct upgrade (demo / test)
    updated = upgrade_plan_manual(db, current_user, data.plan)
    return {
        "plan":       updated.plan.value,
        "message":    f"Successfully upgraded to {updated.plan.value} plan.",
        "expires_at": updated.plan_expires_at.isoformat() if updated.plan_expires_at else None,
    }


# ── POST /subscription/webhook ────────────────────────────────────────────────

@subscription_router.post("/webhook")
async def stripe_webhook(
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    """Receive and process Stripe webhook events."""
    from app.services.subscription_service import handle_stripe_webhook

    payload    = await request.body()
    sig_header = request.headers.get("stripe-signature", "")
    result     = handle_stripe_webhook(db, payload, sig_header)
    return result


# ── GET /usage/me ─────────────────────────────────────────────────────────────

@usage_router.get("/me")
def get_my_usage(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Return the authenticated user's full usage dashboard data:
    monthly totals, daily breakdown, quota progress, and cost.
    """
    from app.services.subscription_service import get_monthly_usage_detail, get_plan_limits
    from app.services.usage_service import get_daily_usage, get_endpoint_breakdown

    limits = get_plan_limits(current_user.plan)
    detail = get_monthly_usage_detail(db, current_user.id)
    daily  = get_daily_usage(db, days=30, user_id=current_user.id)
    by_ep  = get_endpoint_breakdown(db, days=30)  # platform-wide but still useful

    quota_pct = min(100.0, (detail["calls"] / max(limits["monthly_requests"], 1)) * 100)

    return {
        "plan":           current_user.plan.value,
        "plan_label":     limits["label"],
        "monthly_limit":  limits["monthly_requests"],
        "monthly_used":   detail["calls"],
        "monthly_remaining": max(0, limits["monthly_requests"] - detail["calls"]),
        "quota_percent":  round(quota_pct, 1),
        "tokens_used":    detail["tokens_used"],
        "cost_usd":       detail["cost_usd"],
        "period_start":   detail["period_start"],
        "period_end":     detail["period_end"],
        "daily_usage":    daily,
        "by_endpoint":    by_ep,
    }
