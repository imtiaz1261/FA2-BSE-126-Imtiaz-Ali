"""schemas/admin.py — Admin dashboard schemas."""
import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class AdminUserResponse(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    role: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    last_login_at: Optional[datetime] = None
    subscription_plan: Optional[str] = None
    subscription_status: Optional[str] = None
    total_tokens_used: int = 0
    total_requests: int = 0
    model_config = {"from_attributes": True}


class AdminUserListResponse(BaseModel):
    users: list[AdminUserResponse]
    total: int
    page: int
    page_size: int


class AdminUsageMetrics(BaseModel):
    total_users: int
    active_users_today: int
    total_requests_today: int
    total_tokens_today: int
    estimated_cost_today_usd: float
    total_requests_month: int
    total_tokens_month: int
    estimated_cost_month_usd: float
    requests_by_feature: dict[str, int]
    errors_today: int
    guardrail_blocks_today: int


class AdminSubscriptionMetrics(BaseModel):
    free_count: int
    pro_count: int
    enterprise_count: int
    total_active: int
    monthly_revenue_usd: float


class SystemHealthResponse(BaseModel):
    status: str
    database: dict
    redis: dict
    version: str
    environment: str


class AdminUserActionRequest(BaseModel):
    action: str   # disable | enable | promote | demote
