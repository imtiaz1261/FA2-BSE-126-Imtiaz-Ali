"""
Usage recording & analytics service — Phase 17/18.

Records token counts and cost estimates after every LLM call and
provides aggregation queries used by the admin dashboard.

Cost estimation uses approximate per-token pricing.  Real costs should
come from provider invoices; these are useful indicators only.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.models.usage import UsageRecord
from app.models.user import User

# ---------------------------------------------------------------------------
# Token cost table (USD per 1000 tokens, rough approximations)
# ---------------------------------------------------------------------------

_COST_PER_1K: Dict[str, Dict[str, float]] = {
    "gpt-4o": {"input": 0.005, "output": 0.015},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "gpt-4-turbo": {"input": 0.01, "output": 0.03},
    "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
    # Groq models (very cheap)
    "llama-3.3-70b-versatile": {"input": 0.00059, "output": 0.00079},
    "llama-3.1-8b-instant": {"input": 0.00005, "output": 0.00008},
    "openai/gpt-oss-120b": {"input": 0.0009, "output": 0.0009},
    # Embedding
    "text-embedding-3-small": {"input": 0.00002, "output": 0.0},
}

_DEFAULT_COST = {"input": 0.001, "output": 0.002}


def estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Estimate USD cost from token counts and model name."""
    key = model.lower()
    # Try exact match then prefix match
    pricing = _COST_PER_1K.get(key)
    if pricing is None:
        for k, v in _COST_PER_1K.items():
            if key.startswith(k) or k in key:
                pricing = v
                break
    pricing = pricing or _DEFAULT_COST
    return (prompt_tokens * pricing["input"] + completion_tokens * pricing["output"]) / 1000.0


# ---------------------------------------------------------------------------
# Write
# ---------------------------------------------------------------------------


def record_usage(
    db: Session,
    user_id: uuid.UUID,
    endpoint: str,
    tokens_used: int,
    cost_usd: float,
) -> UsageRecord:
    """Persist a usage record for a single LLM call."""
    record = UsageRecord(
        user_id=user_id,
        endpoint=endpoint,
        tokens_used=tokens_used,
        cost_usd=cost_usd,
    )
    db.add(record)
    db.commit()
    return record


# ---------------------------------------------------------------------------
# Analytics queries (admin dashboard)
# ---------------------------------------------------------------------------


def get_daily_usage(
    db: Session,
    days: int = 30,
    user_id: Optional[uuid.UUID] = None,
) -> List[Dict[str, Any]]:
    """
    Daily token counts and costs for the last `days` days.
    If user_id is given, scoped to that user; otherwise platform-wide.
    """
    cutoff = datetime.now(tz=timezone.utc) - timedelta(days=days)
    stmt = (
        select(
            func.date_trunc("day", UsageRecord.created_at).label("day"),
            func.sum(UsageRecord.tokens_used).label("tokens"),
            func.sum(UsageRecord.cost_usd).label("cost"),
            func.count(UsageRecord.id).label("calls"),
        )
        .where(UsageRecord.created_at >= cutoff)
        .group_by("day")
        .order_by("day")
    )
    if user_id:
        stmt = stmt.where(UsageRecord.user_id == user_id)

    rows = db.execute(stmt).all()
    return [
        {
            "day": str(r.day)[:10],
            "tokens": int(r.tokens or 0),
            "cost": round(float(r.cost or 0), 6),
            "calls": int(r.calls or 0),
        }
        for r in rows
    ]


def get_endpoint_breakdown(
    db: Session,
    days: int = 30,
) -> List[Dict[str, Any]]:
    """Token usage grouped by endpoint (chat, rag, agent, embedding)."""
    cutoff = datetime.now(tz=timezone.utc) - timedelta(days=days)
    stmt = (
        select(
            UsageRecord.endpoint,
            func.sum(UsageRecord.tokens_used).label("tokens"),
            func.sum(UsageRecord.cost_usd).label("cost"),
            func.count(UsageRecord.id).label("calls"),
        )
        .where(UsageRecord.created_at >= cutoff)
        .group_by(UsageRecord.endpoint)
        .order_by(func.sum(UsageRecord.tokens_used).desc())
    )
    rows = db.execute(stmt).all()
    return [
        {
            "endpoint": r.endpoint,
            "tokens": int(r.tokens or 0),
            "cost": round(float(r.cost or 0), 6),
            "calls": int(r.calls or 0),
        }
        for r in rows
    ]


def get_top_users_by_cost(
    db: Session,
    days: int = 30,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """Top users by total cost for the last `days` days."""
    cutoff = datetime.now(tz=timezone.utc) - timedelta(days=days)
    stmt = (
        select(
            UsageRecord.user_id,
            User.email,
            User.plan,
            func.sum(UsageRecord.tokens_used).label("tokens"),
            func.sum(UsageRecord.cost_usd).label("cost"),
            func.count(UsageRecord.id).label("calls"),
        )
        .join(User, UsageRecord.user_id == User.id)
        .where(UsageRecord.created_at >= cutoff)
        .group_by(UsageRecord.user_id, User.email, User.plan)
        .order_by(func.sum(UsageRecord.cost_usd).desc())
        .limit(limit)
    )
    rows = db.execute(stmt).all()
    return [
        {
            "user_id": str(r.user_id),
            "email": r.email,
            "plan": r.plan,
            "tokens": int(r.tokens or 0),
            "cost": round(float(r.cost or 0), 6),
            "calls": int(r.calls or 0),
        }
        for r in rows
    ]


def get_user_stats(
    db: Session,
    days: int = 30,
) -> Dict[str, Any]:
    """
    Platform-wide user counts: total, active (used LLM in window),
    by plan tier, new registrations in window.
    """
    from app.models.user import PlanTier

    total = db.scalar(select(func.count(User.id))) or 0
    cutoff = datetime.now(tz=timezone.utc) - timedelta(days=days)

    active_ids = db.scalars(
        select(UsageRecord.user_id)
        .where(UsageRecord.created_at >= cutoff)
        .distinct()
    ).all()
    active = len(active_ids)

    new_users = db.scalar(
        select(func.count(User.id)).where(User.created_at >= cutoff)
    ) or 0

    plan_counts = {}
    for tier in PlanTier:
        plan_counts[tier.value] = (
            db.scalar(select(func.count(User.id)).where(User.plan == tier)) or 0
        )

    total_cost = db.scalar(
        select(func.sum(UsageRecord.cost_usd)).where(UsageRecord.created_at >= cutoff)
    ) or 0.0

    total_tokens = db.scalar(
        select(func.sum(UsageRecord.tokens_used)).where(UsageRecord.created_at >= cutoff)
    ) or 0

    total_calls = db.scalar(
        select(func.count(UsageRecord.id)).where(UsageRecord.created_at >= cutoff)
    ) or 0

    return {
        "total_users": total,
        "active_users": active,
        "new_users": new_users,
        "plan_counts": plan_counts,
        "total_cost_usd": round(float(total_cost), 4),
        "total_tokens": int(total_tokens),
        "total_calls": int(total_calls),
        "window_days": days,
    }


def get_new_users_daily(
    db: Session,
    days: int = 30,
) -> List[Dict[str, Any]]:
    """Daily new user registrations for the last `days` days."""
    cutoff = datetime.now(tz=timezone.utc) - timedelta(days=days)
    stmt = (
        select(
            func.date_trunc("day", User.created_at).label("day"),
            func.count(User.id).label("count"),
        )
        .where(User.created_at >= cutoff)
        .group_by("day")
        .order_by("day")
    )
    rows = db.execute(stmt).all()
    return [{"day": str(r.day)[:10], "count": int(r.count or 0)} for r in rows]


def list_users(
    db: Session,
    limit: int = 100,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    """Paginated user list for the admin panel."""
    from app.models.conversation import Conversation
    from app.models.document import Document

    users = db.scalars(
        select(User).order_by(User.created_at.desc()).limit(limit).offset(offset)
    ).all()

    result = []
    for u in users:
        conv_count = db.scalar(
            select(func.count(Conversation.id)).where(Conversation.user_id == u.id)
        ) or 0
        doc_count = db.scalar(
            select(func.count(Document.id)).where(Document.user_id == u.id)
        ) or 0
        total_tokens = db.scalar(
            select(func.sum(UsageRecord.tokens_used)).where(UsageRecord.user_id == u.id)
        ) or 0
        total_cost = db.scalar(
            select(func.sum(UsageRecord.cost_usd)).where(UsageRecord.user_id == u.id)
        ) or 0.0

        result.append(
            {
                "id": str(u.id),
                "email": u.email,
                "full_name": u.full_name or "",
                "plan": u.plan.value,
                "is_active": u.is_active,
                "is_admin": u.is_admin,
                "created_at": u.created_at.isoformat(),
                "conversations": conv_count,
                "documents": doc_count,
                "total_tokens": int(total_tokens),
                "total_cost": round(float(total_cost), 4),
            }
        )
    return result
