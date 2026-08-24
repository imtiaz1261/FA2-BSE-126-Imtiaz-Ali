"""
services/usage_service.py — Usage Tracking & Enforcement Gate
==============================================================
Every AI request flows through this service:
    check_limits()  → called BEFORE the LLM to gate the request
    log_usage()     → called AFTER the LLM to record what was used

Enforcement gate order (matches spec):
    Auth → Subscription Check → Usage Check → Guardrail → AI
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.core.logging import get_logger
from backend.db.models.subscription import Subscription, SubscriptionPlan
from backend.db.models.usage import AIFeature, RequestStatus, UsageRecord

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Cost table (USD per 1 000 tokens) — update when OpenAI changes pricing
# ---------------------------------------------------------------------------
_COST_PER_1K: dict[str, dict[str, float]] = {
    "gpt-4o-mini":    {"input": 0.000150, "output": 0.000600},
    "gpt-4o":         {"input": 0.005000, "output": 0.015000},
    "gpt-3.5-turbo":  {"input": 0.000500, "output": 0.001500},
}
_DEFAULT_COST = {"input": 0.000150, "output": 0.000600}


def estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> Decimal:
    rates = _COST_PER_1K.get(model, _DEFAULT_COST)
    cost = (prompt_tokens / 1000 * rates["input"]) + (completion_tokens / 1000 * rates["output"])
    return Decimal(str(round(cost, 6)))


# ---------------------------------------------------------------------------
# Plan limits lookup — reads from settings, never hardcoded
# ---------------------------------------------------------------------------
def get_plan_monthly_tokens(plan: SubscriptionPlan) -> int:
    mapping = {
        SubscriptionPlan.FREE:       settings.FREE_PLAN_MONTHLY_TOKENS,
        SubscriptionPlan.PRO:        settings.PRO_PLAN_MONTHLY_TOKENS,
        SubscriptionPlan.ENTERPRISE: settings.ENTERPRISE_PLAN_MONTHLY_TOKENS,
    }
    return mapping.get(plan, settings.FREE_PLAN_MONTHLY_TOKENS)


def get_plan_daily_requests(plan: SubscriptionPlan) -> int:
    mapping = {
        SubscriptionPlan.FREE:       settings.FREE_PLAN_DAILY_REQUESTS,
        SubscriptionPlan.PRO:        settings.PRO_PLAN_DAILY_REQUESTS,
        SubscriptionPlan.ENTERPRISE: settings.ENTERPRISE_PLAN_DAILY_REQUESTS,
    }
    return mapping.get(plan, settings.FREE_PLAN_DAILY_REQUESTS)


def get_plan_doc_limit(plan: SubscriptionPlan) -> int:
    return {
        SubscriptionPlan.FREE: 5,
        SubscriptionPlan.PRO: 50,
        SubscriptionPlan.ENTERPRISE: 500,
    }.get(plan, 5)


# ---------------------------------------------------------------------------
# Enforcement check
# ---------------------------------------------------------------------------
class LimitStatus:
    def __init__(
        self,
        allowed: bool,
        reason: str = "",
        tokens_used: int = 0,
        tokens_limit: int = 0,
        requests_today: int = 0,
        daily_limit: int = 0,
    ):
        self.allowed = allowed
        self.reason = reason
        self.tokens_used = tokens_used
        self.tokens_limit = tokens_limit
        self.requests_today = requests_today
        self.daily_limit = daily_limit


async def check_limits(
    db: AsyncSession,
    user_id: uuid.UUID,
    feature: AIFeature = AIFeature.CHAT,
) -> LimitStatus:
    """
    Gate check before any AI operation.

    Checks:
    1. Subscription exists and is active
    2. Monthly token budget not exhausted
    3. Daily request count not exceeded

    Returns LimitStatus with allowed=True if all checks pass,
    allowed=False with a user-facing reason if any check fails.
    """
    # Load subscription
    sub_result = await db.execute(
        select(Subscription).where(Subscription.user_id == user_id)
    )
    subscription = sub_result.scalar_one_or_none()

    if not subscription or not subscription.is_active:
        return LimitStatus(
            allowed=False,
            reason=(
                "Your subscription is not active. "
                "Please check your account or upgrade your plan to continue."
            ),
        )

    plan = subscription.plan
    monthly_limit = get_plan_monthly_tokens(plan)
    daily_limit = get_plan_daily_requests(plan)

    # Monthly token usage for current billing period
    token_result = await db.execute(
        select(func.coalesce(func.sum(UsageRecord.total_tokens), 0)).where(
            UsageRecord.user_id == user_id,
            UsageRecord.status == RequestStatus.SUCCESS,
            UsageRecord.created_at >= subscription.current_period_start,
            UsageRecord.created_at <= subscription.current_period_end,
        )
    )
    tokens_used: int = token_result.scalar() or 0

    if tokens_used >= monthly_limit:
        return LimitStatus(
            allowed=False,
            tokens_used=tokens_used,
            tokens_limit=monthly_limit,
            reason=(
                f"**Usage limit reached**\n\n"
                f"You have used {tokens_used:,} / {monthly_limit:,} tokens "
                f"this billing period. Please upgrade your plan to continue "
                f"using this feature."
            ),
        )

    # Daily request count
    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    req_result = await db.execute(
        select(func.count(UsageRecord.id)).where(
            UsageRecord.user_id == user_id,
            UsageRecord.feature == feature,
            UsageRecord.created_at >= today_start,
        )
    )
    requests_today: int = req_result.scalar() or 0

    if requests_today >= daily_limit:
        return LimitStatus(
            allowed=False,
            requests_today=requests_today,
            daily_limit=daily_limit,
            reason=(
                f"**Daily request limit reached**\n\n"
                f"You have made {requests_today} / {daily_limit} requests today. "
                f"Your limit resets at midnight UTC or upgrade your plan for more."
            ),
        )

    return LimitStatus(
        allowed=True,
        tokens_used=tokens_used,
        tokens_limit=monthly_limit,
        requests_today=requests_today,
        daily_limit=daily_limit,
    )


# ---------------------------------------------------------------------------
# Log usage after an AI operation
# ---------------------------------------------------------------------------
async def log_usage(
    db: AsyncSession,
    user_id: uuid.UUID,
    feature: AIFeature,
    prompt_tokens: int,
    completion_tokens: int,
    model: str,
    latency_ms: int = 0,
    status: RequestStatus = RequestStatus.SUCCESS,
    conversation_id: Optional[uuid.UUID] = None,
    error_message: Optional[str] = None,
) -> UsageRecord:
    """
    Write one UsageRecord row and update the conversation counters.
    Called after every AI operation — success or failure.
    """
    total_tokens = prompt_tokens + completion_tokens
    cost = estimate_cost(model, prompt_tokens, completion_tokens)

    record = UsageRecord(
        user_id=user_id,
        conversation_id=conversation_id,
        feature=feature,
        status=status,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        estimated_cost_usd=cost,
        model=model,
        latency_ms=latency_ms,
        error_message=error_message,
    )
    db.add(record)
    await db.flush()

    logger.info(
        "usage_logged",
        user_id=str(user_id),
        feature=feature.value,
        total_tokens=total_tokens,
        cost_usd=float(cost),
        status=status.value,
    )
    return record


# ---------------------------------------------------------------------------
# Usage summary for the current user
# ---------------------------------------------------------------------------
async def get_usage_summary(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> dict:
    """Return aggregated usage stats for the current billing period."""
    sub_result = await db.execute(
        select(Subscription).where(Subscription.user_id == user_id)
    )
    subscription = sub_result.scalar_one_or_none()
    if not subscription:
        return {}

    plan = subscription.plan
    monthly_limit = get_plan_monthly_tokens(plan)
    daily_limit = get_plan_daily_requests(plan)
    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    # Tokens this period
    token_q = await db.execute(
        select(func.coalesce(func.sum(UsageRecord.total_tokens), 0)).where(
            UsageRecord.user_id == user_id,
            UsageRecord.status == RequestStatus.SUCCESS,
            UsageRecord.created_at >= subscription.current_period_start,
        )
    )
    tokens_used = int(token_q.scalar() or 0)

    # Cost this period
    cost_q = await db.execute(
        select(
            func.coalesce(func.sum(UsageRecord.estimated_cost_usd), 0)
        ).where(
            UsageRecord.user_id == user_id,
            UsageRecord.status == RequestStatus.SUCCESS,
            UsageRecord.created_at >= subscription.current_period_start,
        )
    )
    total_cost = float(cost_q.scalar() or 0)

    # Requests today
    today_q = await db.execute(
        select(func.count(UsageRecord.id)).where(
            UsageRecord.user_id == user_id,
            UsageRecord.created_at >= today_start,
        )
    )
    requests_today = int(today_q.scalar() or 0)

    # Per-feature counts this period
    feature_q = await db.execute(
        select(UsageRecord.feature, func.count(UsageRecord.id)).where(
            UsageRecord.user_id == user_id,
            UsageRecord.created_at >= subscription.current_period_start,
        ).group_by(UsageRecord.feature)
    )
    feature_counts = {row[0].value: row[1] for row in feature_q.all()}

    # Document count
    from backend.db.models.document import Document
    doc_q = await db.execute(
        select(func.count(Document.id)).where(Document.user_id == user_id)
    )
    doc_count = int(doc_q.scalar() or 0)

    return {
        "plan": plan.value,
        "billing_period_start": subscription.current_period_start,
        "billing_period_end": subscription.current_period_end,
        "tokens_used": tokens_used,
        "tokens_limit": monthly_limit,
        "tokens_remaining": max(0, monthly_limit - tokens_used),
        "tokens_pct": round(min(100, tokens_used / monthly_limit * 100), 1),
        "requests_today": requests_today,
        "daily_request_limit": daily_limit,
        "requests_remaining_today": max(0, daily_limit - requests_today),
        "chat_requests": feature_counts.get("chat", 0),
        "rag_requests": feature_counts.get("rag", 0),
        "agent_requests": feature_counts.get("agent", 0),
        "tool_calls": feature_counts.get("tool_call", 0),
        "documents_uploaded": doc_count,
        "estimated_cost_usd": round(total_cost, 4),
    }


async def get_admin_usage_metrics(db: AsyncSession) -> dict:
    """Aggregated platform-wide metrics for admin dashboard."""
    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    month_start = datetime.now(timezone.utc).replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )

    from backend.db.models.user import User

    total_users_q = await db.execute(select(func.count(User.id)))
    total_users = int(total_users_q.scalar() or 0)

    active_today_q = await db.execute(
        select(func.count(func.distinct(UsageRecord.user_id))).where(
            UsageRecord.created_at >= today_start
        )
    )
    active_today = int(active_today_q.scalar() or 0)

    today_q = await db.execute(
        select(
            func.count(UsageRecord.id),
            func.coalesce(func.sum(UsageRecord.total_tokens), 0),
            func.coalesce(func.sum(UsageRecord.estimated_cost_usd), 0),
        ).where(UsageRecord.created_at >= today_start)
    )
    today_row = today_q.one()

    month_q = await db.execute(
        select(
            func.count(UsageRecord.id),
            func.coalesce(func.sum(UsageRecord.total_tokens), 0),
            func.coalesce(func.sum(UsageRecord.estimated_cost_usd), 0),
        ).where(UsageRecord.created_at >= month_start)
    )
    month_row = month_q.one()

    errors_q = await db.execute(
        select(func.count(UsageRecord.id)).where(
            UsageRecord.created_at >= today_start,
            UsageRecord.status == RequestStatus.ERROR,
        )
    )
    errors = int(errors_q.scalar() or 0)

    blocks_q = await db.execute(
        select(func.count(UsageRecord.id)).where(
            UsageRecord.created_at >= today_start,
            UsageRecord.status.in_([RequestStatus.BLOCKED, RequestStatus.GUARDRAIL_BLOCKED]),
        )
    )
    blocks = int(blocks_q.scalar() or 0)

    feat_q = await db.execute(
        select(UsageRecord.feature, func.count(UsageRecord.id)).where(
            UsageRecord.created_at >= today_start
        ).group_by(UsageRecord.feature)
    )
    by_feature = {row[0].value: row[1] for row in feat_q.all()}

    return {
        "total_users": total_users,
        "active_users_today": active_today,
        "total_requests_today": int(today_row[0]),
        "total_tokens_today": int(today_row[1]),
        "estimated_cost_today_usd": float(today_row[2]),
        "total_requests_month": int(month_row[0]),
        "total_tokens_month": int(month_row[1]),
        "estimated_cost_month_usd": float(month_row[2]),
        "requests_by_feature": by_feature,
        "errors_today": errors,
        "guardrail_blocks_today": blocks,
    }
