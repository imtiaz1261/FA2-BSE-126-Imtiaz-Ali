"""
Pydantic schemas for admin API endpoints.

Schemas for:
- Analytics responses
- User management
- Moderation
- Billing administration
- Audit logs
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ============================================================================
# Analytics Schemas
# ============================================================================


class AnalyticsDataPoint(BaseModel):
    """Single data point in analytics series."""
    date: str


class ActiveUsersData(AnalyticsDataPoint):
    """DAU/MAU data point."""
    dau: int
    mau: int


class MessagesData(AnalyticsDataPoint):
    """Messages per day data point."""
    messages: int


class TokensData(AnalyticsDataPoint):
    """Token usage data point."""
    input_tokens: int
    output_tokens: int
    total_tokens: int


class CostData(AnalyticsDataPoint):
    """Daily cost data point."""
    cost: float


class PlanDistributionData(BaseModel):
    """Plan distribution data point."""
    plan: str
    users: int
    percentage: float


class ChurnData(BaseModel):
    """Monthly churn rate."""
    month: str
    churn_rate: float


class RetentionCohort(BaseModel):
    """Retention cohort data."""
    cohort: str
    users: int
    week_0: int
    week_1: int
    week_2: int
    week_3: int


class OverviewMetrics(BaseModel):
    """High-level platform KPIs."""
    dau: int
    mau: int
    messages_today: int
    tokens_today: int
    estimated_cost_today: float
    paid_subscriptions: int
    monthly_churn_rate: float
    new_users_today: int


class AnalyticsResponse(BaseModel):
    """Generic analytics response container."""
    data: list[dict] = Field(default_factory=list)
    total: Optional[int] = None
    total_cost: Optional[float] = None


# ============================================================================
# User Management Schemas
# ============================================================================


class UserListItem(BaseModel):
    """User item in list response."""
    id: UUID
    email: str
    name: Optional[str]
    plan: str
    status: str
    messages_used_today: int
    joined_at: datetime
    last_active_at: Optional[datetime]
    role: str = "user"


class UsersListResponse(BaseModel):
    """List of users with pagination."""
    items: list[UserListItem]
    page: int
    page_size: int
    total: int


class UserActivity(BaseModel):
    """User activity entry."""
    type: str  # conversation, message, agent_run, billing_event
    description: str
    timestamp: datetime
    metadata: dict = {}


class UserDetailResponse(BaseModel):
    """Complete user details."""
    id: UUID
    email: str
    name: Optional[str]
    role: str
    status: str
    is_verified: bool
    joined_at: datetime
    last_active_at: Optional[datetime]

    # Subscription
    plan: str
    subscription_status: str
    renewal_date: Optional[datetime]
    stripe_customer_id: Optional[str]
    cancel_at_period_end: bool

    # Usage
    messages_today: int
    messages_this_month: int
    tokens_used: int
    estimated_cost: float
    agent_runs: int
    rag_queries: int

    # Recent activity
    recent_conversations: int
    recent_messages: int

    class Config:
        from_attributes = True


# ============================================================================
# User Actions Schemas
# ============================================================================


class SuspendUserRequest(BaseModel):
    """Request to suspend a user."""
    reason: str


class SuspendUserResponse(BaseModel):
    """Response to suspend a user."""
    success: bool
    status: str
    message: str


class BanUserRequest(BaseModel):
    """Request to ban a user."""
    reason: str


class BanUserResponse(BaseModel):
    """Response to ban a user."""
    success: bool
    status: str
    message: str


class ChangePlanRequest(BaseModel):
    """Request to change user's plan."""
    plan: str  # free, plus, pro


class ChangePlanResponse(BaseModel):
    """Response to plan change."""
    success: bool
    new_plan: str
    message: str


class RefundRequest(BaseModel):
    """Request to issue a refund."""
    payment_intent_id: str
    amount: Optional[float] = None  # None for full refund
    reason: str


class RefundResponse(BaseModel):
    """Response to refund request."""
    success: bool
    refund_id: str
    status: str
    amount: float
    message: str


# ============================================================================
# Moderation Schemas
# ============================================================================


class ModerationFlagResponse(BaseModel):
    """Moderation flag in queue."""
    id: UUID
    conversation_id: UUID
    user_id: UUID
    category: str
    severity: str  # low, medium, high, critical
    reason: Optional[str]
    status: str  # pending, approved, banned, dismissed
    created_at: datetime
    reviewed_at: Optional[datetime]

    class Config:
        from_attributes = True


class ModerationDetailsResponse(BaseModel):
    """Full moderation flag details with conversation."""
    flag: ModerationFlagResponse
    user_email: str
    user_name: Optional[str]
    conversation_title: Optional[str]
    message_count: int
    recent_messages: list[dict]


class ApproveModerationRequest(BaseModel):
    """Request to approve a moderation flag."""
    note: str


class ApproveModerationResponse(BaseModel):
    """Response to approve moderation."""
    success: bool
    status: str
    message: str


class BanModeratedUserRequest(BaseModel):
    """Request to ban user from moderation flag."""
    reason: str


class BanModeratedUserResponse(BaseModel):
    """Response to ban moderated user."""
    success: bool
    status: str
    user_banned: bool
    message: str


# ============================================================================
# Model Performance Schemas
# ============================================================================


class ModelPerformanceData(BaseModel):
    """Model performance statistics."""
    model: str
    requests: int
    success_rate: float
    error_rate: float
    avg_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    input_tokens: int
    output_tokens: int
    total_tokens: int
    estimated_cost: float


class ModelPerformanceResponse(BaseModel):
    """Model performance metrics response."""
    models: list[ModelPerformanceData]


# ============================================================================
# Audit Log Schemas
# ============================================================================


class AuditLogEntry(BaseModel):
    """Single audit log entry."""
    id: UUID
    admin_user_id: UUID
    target_user_id: Optional[UUID]
    action: str
    reason: Optional[str]
    metadata: dict
    created_at: datetime

    class Config:
        from_attributes = True


class AuditLogResponse(BaseModel):
    """Audit log response with pagination."""
    items: list[AuditLogEntry]
    page: int
    page_size: int
    total: int
