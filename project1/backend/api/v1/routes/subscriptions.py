"""
api/v1/routes/subscriptions.py — Subscription & Usage Endpoints
================================================================
Routes:
    GET  /subscriptions/plans          List all plans + limits
    GET  /subscriptions/me             Current user subscription
    GET  /subscriptions/usage          Current usage summary
    POST /subscriptions/upgrade        Create Stripe checkout session
    POST /subscriptions/cancel         Cancel subscription
    POST /subscriptions/webhook        Stripe webhook handler
    GET  /subscriptions/mock-checkout  Dev-only mock upgrade
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.dependencies import get_current_active_user, get_db
from backend.core.logging import get_logger
from backend.db.models.user import User
from backend.schemas.subscription import (
    CheckoutSessionResponse,
    PlanLimits,
    SubscriptionResponse,
    UpgradeRequest,
    UsageSummaryResponse,
)
from backend.services import subscription_service, usage_service

router = APIRouter(prefix="/subscriptions", tags=["Subscriptions"])
logger = get_logger(__name__)


@router.get("/plans", response_model=list[PlanLimits], summary="List all subscription plans")
async def list_plans() -> list[PlanLimits]:
    return subscription_service.ALL_PLANS


@router.get("/me", response_model=SubscriptionResponse, summary="Get current subscription")
async def get_my_subscription(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> SubscriptionResponse:
    sub = await subscription_service.get_subscription(db, current_user.id)
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")

    limits = subscription_service.get_plan_limits(sub.plan.value)
    return SubscriptionResponse(
        id=sub.id,
        plan=sub.plan.value,
        status=sub.status.value,
        current_period_start=sub.current_period_start,
        current_period_end=sub.current_period_end,
        days_remaining=sub.days_remaining,
        stripe_customer_id=sub.stripe_customer_id,
        is_active=sub.is_active,
        is_paid=sub.is_paid,
        limits=limits,
    )


@router.get("/usage", response_model=UsageSummaryResponse, summary="Get usage summary")
async def get_usage_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> UsageSummaryResponse:
    summary = await usage_service.get_usage_summary(db, current_user.id)
    if not summary:
        raise HTTPException(status_code=404, detail="Usage data not found")
    return UsageSummaryResponse(**summary)


@router.post("/upgrade", response_model=CheckoutSessionResponse, summary="Upgrade plan")
async def upgrade_plan(
    body: UpgradeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> CheckoutSessionResponse:
    try:
        checkout_url = await subscription_service.create_checkout_session(
            plan=body.plan, user_id=current_user.id
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Checkout session failed: {exc}")
    return CheckoutSessionResponse(checkout_url=checkout_url, plan=body.plan)


@router.post("/cancel", summary="Cancel subscription")
async def cancel_subscription(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    await subscription_service.cancel_subscription(db, current_user.id)
    return {"message": "Subscription cancelled. You retain access until the end of the billing period."}


@router.post("/webhook", include_in_schema=False)
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)) -> dict:
    """Handle Stripe webhook events."""
    from backend.core.config import settings
    try:
        import stripe
        payload = await request.body()
        sig = request.headers.get("stripe-signature", "")
        event = stripe.Webhook.construct_event(payload, sig, settings.STRIPE_WEBHOOK_SECRET)

        if event["type"] == "checkout.session.completed":
            session = event["data"]["object"]
            user_id = uuid.UUID(session["metadata"]["user_id"])
            plan = session["metadata"]["plan"]
            await subscription_service.handle_webhook_upgrade(
                db, user_id, plan,
                stripe_customer_id=session.get("customer"),
                stripe_subscription_id=session.get("subscription"),
            )
            await db.commit()
        return {"status": "ok"}
    except Exception as exc:
        logger.error("stripe_webhook_failed", error=str(exc))
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/mock-checkout", include_in_schema=False)
async def mock_checkout(
    plan: str = Query(...),
    user: str = Query(...),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Development-only mock checkout — instantly upgrades the user."""
    try:
        user_id = uuid.UUID(user)
        await subscription_service.handle_webhook_upgrade(db, user_id, plan)
        await db.commit()
        return {"message": f"Plan upgraded to {plan}", "user_id": user, "plan": plan}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/ping", include_in_schema=False)
async def ping():
    return {"router": "subscriptions", "status": "ok"}
