"""
api/v1/routes/admin.py — Admin Dashboard Endpoints (admin role required)
=========================================================================
Routes:
    GET  /admin/users                 List all users
    GET  /admin/users/{id}            Get user details
    POST /admin/users/{id}/action     Disable/enable/promote/demote
    GET  /admin/metrics/usage         Platform usage metrics
    GET  /admin/metrics/subscriptions Subscription breakdown
    GET  /admin/health                System health check
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.dependencies import get_current_admin_user, get_db
from backend.core.logging import get_logger
from backend.db.models.user import User, UserRole
from backend.db.models.subscription import Subscription
from backend.db.models.usage import UsageRecord
from backend.schemas.admin import (
    AdminUsageMetrics,
    AdminUserActionRequest,
    AdminUserListResponse,
    AdminUserResponse,
    SystemHealthResponse,
)
from backend.services import usage_service, subscription_service
from sqlalchemy import func

router = APIRouter(prefix="/admin", tags=["Admin"])
logger = get_logger(__name__)


async def _build_admin_user(db: AsyncSession, user: User) -> AdminUserResponse:
    """Enrich a User with subscription and usage stats."""
    sub_result = await db.execute(
        select(Subscription).where(Subscription.user_id == user.id)
    )
    sub = sub_result.scalar_one_or_none()

    token_result = await db.execute(
        select(func.coalesce(func.sum(UsageRecord.total_tokens), 0)).where(
            UsageRecord.user_id == user.id
        )
    )
    total_tokens = int(token_result.scalar() or 0)

    req_result = await db.execute(
        select(func.count(UsageRecord.id)).where(UsageRecord.user_id == user.id)
    )
    total_requests = int(req_result.scalar() or 0)

    return AdminUserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role.value,
        is_active=user.is_active,
        is_verified=user.is_verified,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
        subscription_plan=sub.plan.value if sub else None,
        subscription_status=sub.status.value if sub else None,
        total_tokens_used=total_tokens,
        total_requests=total_requests,
    )


@router.get("/users", response_model=AdminUserListResponse, summary="List all users")
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str = Query(None),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin_user),
) -> AdminUserListResponse:
    q = select(User)
    if search:
        q = q.where(
            (User.email.ilike(f"%{search}%")) |
            (User.full_name.ilike(f"%{search}%"))
        )
    q = q.order_by(User.created_at.desc())

    count_q = select(func.count()).select_from(q.subquery())
    total = int((await db.execute(count_q)).scalar() or 0)

    q = q.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(q)
    users = result.scalars().all()

    admin_users = []
    for u in users:
        admin_users.append(await _build_admin_user(db, u))

    return AdminUserListResponse(
        users=admin_users,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/users/{user_id}", response_model=AdminUserResponse, summary="Get user detail")
async def get_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin_user),
) -> AdminUserResponse:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return await _build_admin_user(db, user)


@router.post("/users/{user_id}/action", summary="Perform admin action on user")
async def user_action(
    user_id: uuid.UUID,
    body: AdminUserActionRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
) -> dict:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot modify your own account")

    actions = {
        "disable":  lambda: setattr(user, "is_active", False),
        "enable":   lambda: setattr(user, "is_active", True),
        "promote":  lambda: setattr(user, "role", UserRole.ADMIN),
        "demote":   lambda: setattr(user, "role", UserRole.USER),
    }
    if body.action not in actions:
        raise HTTPException(status_code=400, detail=f"Unknown action: {body.action}")

    actions[body.action]()
    await db.flush()
    logger.info("admin_user_action", admin=str(admin.id), target=str(user_id), action=body.action)
    return {"message": f"Action '{body.action}' applied to user {user.email}"}


@router.get("/metrics/usage", response_model=AdminUsageMetrics, summary="Platform usage metrics")
async def get_usage_metrics(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin_user),
) -> AdminUsageMetrics:
    metrics = await usage_service.get_admin_usage_metrics(db)
    return AdminUsageMetrics(**metrics)


@router.get("/metrics/subscriptions", summary="Subscription breakdown")
async def get_subscription_metrics(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin_user),
) -> dict:
    from backend.db.models.subscription import SubscriptionPlan, SubscriptionStatus
    rows = await db.execute(
        select(Subscription.plan, func.count(Subscription.id))
        .where(Subscription.status == SubscriptionStatus.ACTIVE)
        .group_by(Subscription.plan)
    )
    counts = {row[0].value: row[1] for row in rows.all()}
    return {
        "free_count":       counts.get("free", 0),
        "pro_count":        counts.get("pro", 0),
        "enterprise_count": counts.get("enterprise", 0),
        "total_active":     sum(counts.values()),
        "monthly_revenue_usd": counts.get("pro", 0) * 29 + counts.get("enterprise", 0) * 99,
    }


@router.get("/health", response_model=SystemHealthResponse, summary="System health")
async def system_health(
    _admin: User = Depends(get_current_admin_user),
) -> SystemHealthResponse:
    import time
    from backend.db.session import check_db_connection
    from backend.main import check_redis_connection
    from backend.core.config import settings

    t0 = time.monotonic()
    db_ok = await check_db_connection()
    db_ms = round((time.monotonic() - t0) * 1000, 2)

    t0 = time.monotonic()
    redis_ok = await check_redis_connection()
    redis_ms = round((time.monotonic() - t0) * 1000, 2)

    return SystemHealthResponse(
        status="healthy" if (db_ok and redis_ok) else "degraded",
        database={"status": "ok" if db_ok else "error", "latency_ms": db_ms},
        redis={"status": "ok" if redis_ok else "error", "latency_ms": redis_ms},
        version=settings.APP_VERSION,
        environment=settings.APP_ENV,
    )


@router.get("/ping", include_in_schema=False)
async def ping():
    return {"router": "admin", "status": "ok"}
