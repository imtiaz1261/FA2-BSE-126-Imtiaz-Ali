"""
FastAPI routes for Billing & Subscription Management.

Endpoints:
- GET /billing/plans - List all subscription plans
- GET /billing/usage - Get current user's usage
- GET /billing/subscription - Get current subscription
- POST /billing/checkout-session - Create Stripe Checkout session
- POST /billing/portal - Create Stripe Customer Portal link
"""

import logging
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models import User
from app.schemas_billing import (
    CheckoutSessionRequest,
    CheckoutSessionResponse,
    PlansResponse,
    PlanInfo,
    SubscriptionResponse,
    UsageResponse,
    CustomerPortalResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing", tags=["billing"])


# ============================================================================
# Plans Endpoint
# ============================================================================


@router.get("/plans", response_model=PlansResponse)
async def list_plans():
    """
    Get all available subscription plans.

    Returns pricing, features, and limits for Free, Plus, and Pro tiers.
    No authentication required.
    """
    free_plan = PlanInfo(
        name="Free",
        price=0,
        currency="USD",
        interval="month",
        daily_messages=10,
        description="Perfect for trying out",
        features=["10 messages/day", "Basic support"],
        stripe_price_id=None,
    )
    
    plus_plan = PlanInfo(
        name="Plus",
        price=1999,  # $19.99/month in cents
        currency="USD",
        interval="month",
        daily_messages=100,
        description="For active users",
        features=["100 messages/day", "Priority support"],
        stripe_price_id="price_plus",
    )
    
    pro_plan = PlanInfo(
        name="Pro",
        price=9999,  # $99.99/month in cents
        currency="USD",
        interval="month",
        daily_messages=1000,
        description="For power users",
        features=["Unlimited messages", "24/7 support"],
        stripe_price_id="price_pro",
    )
    
    return PlansResponse(
        free=free_plan,
        plus=plus_plan,
        pro=pro_plan,
    )


# ============================================================================
# Usage Endpoint
# ============================================================================


@router.get("/usage", response_model=UsageResponse)
async def get_usage(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get current user's message usage for today.

    Returns current count, daily limit, and percentage used.
    """
    try:
        # For now, return mock data - implement actual usage tracking later
        return UsageResponse(
            plan="free",
            used=5,
            limit=10,
            remaining=5,
            percentage=50,
            reset_at=datetime.now(timezone.utc) + timedelta(hours=24),
        )
    except Exception as e:
        logger.error(f"Error getting usage: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get usage information",
        )


# ============================================================================
# Subscription Endpoint
# ============================================================================


@router.get("/subscription", response_model=SubscriptionResponse)
async def get_subscription(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get current user's subscription information.
    """
    try:
        # Return mock subscription for now
        return SubscriptionResponse(
            plan="free",
            status="active",
            stripe_customer_id=None,
            stripe_subscription_id=None,
            current_period_start=datetime.now(timezone.utc),
            current_period_end=datetime.now(timezone.utc) + timedelta(days=30),
            cancel_at_period_end=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
    except Exception as e:
        logger.error(f"Error getting subscription: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get subscription information",
        )


# ============================================================================
# Checkout Session Endpoint
# ============================================================================


@router.post("/checkout-session", response_model=CheckoutSessionResponse)
async def create_checkout_session(
    request: CheckoutSessionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a Stripe checkout session for subscription upgrade.
    
    Args:
        request: CheckoutSessionRequest with price_id
        
    Returns:
        CheckoutSessionResponse with Stripe checkout URL
    """
    try:
        # Mock checkout URL for now
        checkout_url = f"https://checkout.stripe.com/pay/mock_{request.price_id}"
        return CheckoutSessionResponse(checkout_url=checkout_url)
    except Exception as e:
        logger.error(f"Error creating checkout session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create checkout session",
        )


# ============================================================================
# Customer Portal Endpoint
# ============================================================================


@router.post("/portal", response_model=CustomerPortalResponse)
async def create_portal_session(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a link to Stripe Customer Portal for subscription management.
    
    Returns:
        CustomerPortalResponse with portal URL
    """
    try:
        # Mock portal URL for now
        portal_url = f"https://billing.stripe.com/mock_portal"
        return CustomerPortalResponse(portal_url=portal_url)
    except Exception as e:
        logger.error(f"Error creating portal session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create portal session",
        )
