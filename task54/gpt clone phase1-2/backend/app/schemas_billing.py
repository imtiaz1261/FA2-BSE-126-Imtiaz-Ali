"""
Billing & subscription schemas (Pydantic).
Request/response validation and documentation.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CheckoutSessionRequest(BaseModel):
    """Request to create checkout session."""
    price_id: str = Field(..., description="Stripe price ID")


class CheckoutSessionResponse(BaseModel):
    """Response with checkout URL."""
    checkout_url: str = Field(..., description="Stripe Checkout URL")


class CustomerPortalResponse(BaseModel):
    """Response with customer portal URL."""
    portal_url: str = Field(..., description="Stripe Customer Portal URL")


class PlanInfo(BaseModel):
    """Plan information."""
    name: str = Field(..., description="Plan name")
    price: int = Field(..., description="Price in cents")
    currency: str = Field(..., description="Currency code (USD)")
    interval: str = Field(..., description="Billing interval (month, year)")
    daily_messages: int = Field(..., description="Daily message limit")
    description: str = Field(..., description="Plan description")
    features: list[str] = Field(..., description="Plan features")
    stripe_price_id: Optional[str] = Field(None, description="Stripe price ID")


class PlansResponse(BaseModel):
    """Response with all plans."""
    free: PlanInfo
    plus: PlanInfo
    pro: PlanInfo


class UsageResponse(BaseModel):
    """Current usage information."""
    plan: str = Field(..., description="Current plan (free, plus, pro)")
    used: int = Field(..., description="Messages used today")
    limit: int = Field(..., description="Daily message limit")
    remaining: int = Field(..., description="Messages remaining")
    percentage: int = Field(..., description="Usage as percentage (0-100)")
    reset_at: datetime = Field(..., description="Time when limit resets (UTC)")


class SubscriptionResponse(BaseModel):
    """Subscription information."""
    plan: str = Field(..., description="Plan (free, plus, pro)")
    status: str = Field(..., description="Subscription status")
    stripe_customer_id: Optional[str] = Field(None, description="Stripe customer ID")
    stripe_subscription_id: Optional[str] = Field(None, description="Stripe subscription ID")
    current_period_start: Optional[datetime] = Field(None, description="Period start date")
    current_period_end: Optional[datetime] = Field(None, description="Period end date")
    cancel_at_period_end: bool = Field(False, description="Scheduled for cancellation")
    created_at: datetime = Field(..., description="Created timestamp")
    updated_at: datetime = Field(..., description="Updated timestamp")


class UsageLimitExceededError(BaseModel):
    """Error response when usage limit exceeded."""
    error: str = Field("usage_limit_reached")
    message: str = Field("You have reached your daily message limit.")
    plan: str = Field(..., description="Current plan")
    limit: int = Field(..., description="Daily limit")
    used: int = Field(..., description="Messages used")
    remaining: int = Field(0)
    upgrade_required: bool = Field(True)


class ErrorResponse(BaseModel):
    """Generic error response."""
    error: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Additional details")
