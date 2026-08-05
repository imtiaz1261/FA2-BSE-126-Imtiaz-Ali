"""
Admin API router — Phase 18.

All endpoints require is_admin == True (enforced by get_current_admin).

Endpoints
---------
GET  /admin/stats              — platform-wide headline stats
GET  /admin/users              — paginated user list
GET  /admin/users/{id}         — single user detail
POST /admin/users/{id}/toggle-active  — activate / deactivate user
POST /admin/users/{id}/toggle-admin   — grant / revoke admin
GET  /admin/analytics/usage/daily     — daily token + cost time-series
GET  /admin/analytics/usage/endpoints — breakdown by endpoint
GET  /admin/analytics/usage/top-users — top spenders
GET  /admin/analytics/users/daily     — daily new user registrations
"""

import uuid
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.db.session import get_db
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


# ---------------------------------------------------------------------------
# Headline stats
# ---------------------------------------------------------------------------


@router.get("/stats")
def get_platform_stats(
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin),
) -> dict:
    """Return platform-wide headline metrics for the admin dashboard."""
    from app.services.usage_service import get_user_stats

    return get_user_stats(db, days=days)


# ---------------------------------------------------------------------------
# User management
# ---------------------------------------------------------------------------


@router.get("/users")
def list_users(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin),
) -> list[dict]:
    from app.services.usage_service import list_users as _list

    return _list(db, limit=limit, offset=offset)


@router.get("/users/{user_id}")
def get_user_detail(
    user_id: uuid.UUID,
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin),
) -> dict:
    from sqlalchemy import func, select

    from app.models.conversation import Conversation
    from app.models.document import Document
    from app.models.usage import UsageRecord

    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    from app.services.usage_service import get_daily_usage

    daily = get_daily_usage(db, days=days, user_id=user_id)

    return {
        "id": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
        "plan": user.plan.value,
        "is_active": user.is_active,
        "is_admin": user.is_admin,
        "created_at": user.created_at.isoformat(),
        "conversations": db.scalar(
            select(func.count(Conversation.id)).where(Conversation.user_id == user_id)
        ) or 0,
        "documents": db.scalar(
            select(func.count(Document.id)).where(Document.user_id == user_id)
        ) or 0,
        "daily_usage": daily,
    }


@router.post("/users/{user_id}/toggle-active")
def toggle_user_active(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
) -> dict:
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot deactivate yourself.")
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = not user.is_active
    db.commit()
    logger.info("Admin %s toggled active=%s for user %s", admin.email, user.is_active, user.email)
    return {"id": str(user.id), "is_active": user.is_active}


@router.post("/users/{user_id}/toggle-admin")
def toggle_user_admin(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
) -> dict:
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot change your own admin status.")
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_admin = not user.is_admin
    db.commit()
    logger.info("Admin %s toggled is_admin=%s for user %s", admin.email, user.is_admin, user.email)
    return {"id": str(user.id), "is_admin": user.is_admin}


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------


@router.get("/analytics/usage/daily")
def daily_usage(
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin),
) -> list[dict]:
    from app.services.usage_service import get_daily_usage

    return get_daily_usage(db, days=days)


@router.get("/analytics/usage/endpoints")
def endpoint_breakdown(
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin),
) -> list[dict]:
    from app.services.usage_service import get_endpoint_breakdown

    return get_endpoint_breakdown(db, days=days)


@router.get("/analytics/usage/top-users")
def top_users(
    days: int = Query(default=30, ge=1, le=365),
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin),
) -> list[dict]:
    from app.services.usage_service import get_top_users_by_cost

    return get_top_users_by_cost(db, days=days, limit=limit)


@router.get("/analytics/users/daily")
def daily_new_users(
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin),
) -> list[dict]:
    from app.services.usage_service import get_new_users_daily

    return get_new_users_daily(db, days=days)


# ── Security analytics (Phase 14) ─────────────────────────────────────────────

@router.get("/analytics/security/summary")
def security_summary(
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin),
) -> dict:
    from app.services.security_service import get_security_summary
    return get_security_summary(db, days=days)


@router.get("/analytics/security/events")
def recent_security_events(
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin),
) -> list[dict]:
    from app.services.security_service import get_recent_events
    return get_recent_events(db, limit=limit)


@router.get("/analytics/security/daily")
def daily_security_events(
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin),
) -> list[dict]:
    from app.services.security_service import get_daily_events
    return get_daily_events(db, days=days)
