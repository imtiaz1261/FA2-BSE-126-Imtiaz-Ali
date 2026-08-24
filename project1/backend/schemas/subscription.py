"""schemas/subscription.py — Subscription and usage schemas."""
import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class PlanLimits(BaseModel):
    plan: str
    monthly_tokens: int
    daily_requests: int
    max_document_uploads: int
    max_file_size_mb: int
    rag_enabled: bool
    agents_enabled: bool


class SubscriptionResponse(BaseModel):
    id: uuid.UUID
    plan: str
    status: str
    current_period_start: datetime
    current_period_end: datetime
    days_remaining: int
    stripe_customer_id: Optional[str] = None
    is_active: bool
    is_paid: bool
    limits: PlanLimits
    model_config = {"from_attributes": True}


class UsageSummaryResponse(BaseModel):
    plan: str
    billing_period_start: datetime
    billing_period_end: datetime
    # Token usage
    tokens_used: int
    tokens_limit: int
    tokens_remaining: int
    tokens_pct: float
    # Daily requests
    requests_today: int
    daily_request_limit: int
    requests_remaining_today: int
    # Feature breakdown
    chat_requests: int
    rag_requests: int
    agent_requests: int
    tool_calls: int
    # Documents
    documents_uploaded: int
    # Cost
    estimated_cost_usd: float


class UpgradeRequest(BaseModel):
    plan: str   # pro | enterprise

    @classmethod
    def validate_plan(cls, v: str) -> str:
        if v not in ("pro", "enterprise"):
            raise ValueError("Plan must be pro or enterprise")
        return v


class CheckoutSessionResponse(BaseModel):
    checkout_url: str
    plan: str
