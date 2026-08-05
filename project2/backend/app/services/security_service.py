"""
Security event logging service — Phase 14.
Persists every guardrail decision to the security_events table.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.security_event import EventSeverity, SecurityEvent

logger = logging.getLogger(__name__)


def log_security_event(
    db: Session,
    category: str,
    severity: str,
    action: str,
    reason: str,
    input_snippet: str = "",
    endpoint: str = "",
    user_id: Optional[uuid.UUID] = None,
) -> None:
    """Persist a single security event. Non-fatal — never raises."""
    try:
        sev = EventSeverity(severity) if severity in EventSeverity._value2member_map_ else EventSeverity.MEDIUM
        event = SecurityEvent(
            user_id=user_id,
            category=category,
            severity=sev,
            action=action,
            reason=reason,
            input_snippet=input_snippet[:300],
            endpoint=endpoint,
        )
        db.add(event)
        db.commit()
    except Exception as exc:
        logger.warning("Security event logging failed (non-fatal): %s", exc)


# ── Admin analytics ────────────────────────────────────────────────────────────


def get_security_summary(db: Session, days: int = 30) -> Dict[str, Any]:
    cutoff = datetime.now(tz=timezone.utc) - timedelta(days=days)
    total = db.scalar(
        select(func.count(SecurityEvent.id)).where(SecurityEvent.created_at >= cutoff)
    ) or 0

    by_category = {}
    rows = db.execute(
        select(SecurityEvent.category, func.count(SecurityEvent.id).label("n"))
        .where(SecurityEvent.created_at >= cutoff)
        .group_by(SecurityEvent.category)
        .order_by(func.count(SecurityEvent.id).desc())
    ).all()
    for r in rows:
        by_category[r.category] = int(r.n)

    by_severity = {}
    rows2 = db.execute(
        select(SecurityEvent.severity, func.count(SecurityEvent.id).label("n"))
        .where(SecurityEvent.created_at >= cutoff)
        .group_by(SecurityEvent.severity)
    ).all()
    for r in rows2:
        by_severity[r.severity] = int(r.n)

    return {
        "total_events": total,
        "by_category": by_category,
        "by_severity": by_severity,
        "window_days": days,
    }


def get_recent_events(db: Session, limit: int = 50) -> List[Dict[str, Any]]:
    rows = db.scalars(
        select(SecurityEvent)
        .order_by(SecurityEvent.created_at.desc())
        .limit(limit)
    ).all()
    return [
        {
            "id": str(e.id),
            "user_id": str(e.user_id) if e.user_id else None,
            "category": e.category,
            "severity": e.severity,
            "action": e.action,
            "reason": e.reason,
            "input_snippet": e.input_snippet,
            "endpoint": e.endpoint,
            "created_at": e.created_at.isoformat(),
        }
        for e in rows
    ]


def get_daily_events(db: Session, days: int = 30) -> List[Dict[str, Any]]:
    cutoff = datetime.now(tz=timezone.utc) - timedelta(days=days)
    rows = db.execute(
        select(
            func.date_trunc("day", SecurityEvent.created_at).label("day"),
            func.count(SecurityEvent.id).label("count"),
        )
        .where(SecurityEvent.created_at >= cutoff)
        .group_by("day")
        .order_by("day")
    ).all()
    return [{"day": str(r.day)[:10], "count": int(r.count)} for r in rows]
