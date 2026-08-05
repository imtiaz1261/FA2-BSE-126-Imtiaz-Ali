"""
Research router — Phase 13 / 14 / 15.

POST /research/run     — full blocking run, returns JSON report
POST /research/stream  — streams ResearchEvent markers as text/plain

Phase 14: input guard runs before every research request.
Phase 15: monthly quota and "research" feature-flag enforced before processing.

Wire protocol (one JSON marker per line):
    <!--RESEARCH:{"type":"step",    "step":"Planning research","detail":"..."}-->
    <!--RESEARCH:{"type":"sources", "sources":[...]}-->
    <!--RESEARCH:{"type":"report",  "report":"# ...", "sources":[...]}-->
    <!--RESEARCH:{"type":"error",   "message":"..."}-->
"""

import json
import logging
import time
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/research", tags=["research"])

_MARKER_PREFIX = "<!--RESEARCH:"
_MARKER_SUFFIX = "-->"


def _format(event: dict) -> str:
    return f"{_MARKER_PREFIX}{json.dumps(event, ensure_ascii=False)}{_MARKER_SUFFIX}\n"


# ── helpers ────────────────────────────────────────────────────────────────────

def _enforce_research_access(db: Session, user: User) -> None:
    """Phase 15: quota + feature-flag check. Raises HTTP 429/403 on violation."""
    from app.services.subscription_service import check_feature_access, check_quota
    ok, msg = check_quota(db, user)
    if not ok:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=msg)
    ok2, msg2 = check_feature_access(user, "research")
    if not ok2:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=msg2)


async def _input_guard(text: str, db: Session, user_id: uuid.UUID) -> None:
    """Phase 14: block malicious research queries."""
    try:
        from app.guardrails.input_guard import check_input
        from app.services.security_service import log_security_event
        result = await check_input(text)
        if result.blocked:
            log_security_event(
                db, category=result.category, severity=result.severity,
                action="blocked", reason=result.reason,
                input_snippet=text[:200], endpoint="research", user_id=user_id,
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "blocked": True,
                    "category": result.category,
                    "message": f"Request blocked: {result.reason}",
                },
            )
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("Research input guard error (non-fatal): %s", exc)


# ── request schema ─────────────────────────────────────────────────────────────

class ResearchRequest(BaseModel):
    query: str = Field(min_length=3, max_length=2000)
    conversation_id: str | None = None


# ── blocking run ───────────────────────────────────────────────────────────────

@router.post("/run")
async def run_research(
    data: ResearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Full blocking research run. Returns complete JSON report."""
    _enforce_research_access(db, current_user)
    await _input_guard(data.query, db, current_user.id)

    from app.services.langfuse_service import create_trace, flush, get_langfuse
    from app.services.research_service import run_research as _run

    lf    = get_langfuse()
    trace = create_trace(lf, name="research-run", user_id=str(current_user.id),
                         metadata={"query": data.query[:200]}, tags=["research"])

    final_report = ""
    sources: list = []
    t0 = time.monotonic()

    async for event in _run(data.query, trace=trace):
        if event["type"] == "report":
            final_report = event["report"]
            sources      = event.get("sources", [])
        elif event["type"] == "error":
            flush(lf)
            raise HTTPException(status_code=500, detail=event["message"])

    latency = int((time.monotonic() - t0) * 1000)
    flush(lf)
    _record_research_usage(db, current_user.id, final_report, latency)

    return {"report": final_report, "sources": sources, "latency_ms": latency}


# ── streaming run ──────────────────────────────────────────────────────────────

@router.post("/stream")
async def stream_research(
    data: ResearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    """Stream research progress as <!--RESEARCH:{...}--> markers."""
    _enforce_research_access(db, current_user)
    await _input_guard(data.query, db, current_user.id)

    from app.services.langfuse_service import create_trace, flush, get_langfuse
    from app.services.research_service import run_research as _run

    lf    = get_langfuse()
    trace = create_trace(lf, name="research-stream", user_id=str(current_user.id),
                         metadata={"query": data.query[:200]}, tags=["research","stream"])
    t0 = time.monotonic()

    async def generator():
        final_report = ""
        try:
            async for event in _run(data.query, trace=trace):
                yield _format(event)
                if event["type"] == "report":
                    final_report = event.get("report", "")
        except Exception as exc:
            logger.exception("Research stream failed")
            yield _format({"type": "error", "message": str(exc)})
        finally:
            flush(lf)
            latency = int((time.monotonic() - t0) * 1000)
            _record_research_usage(db, current_user.id, final_report, latency)

    return StreamingResponse(generator(), media_type="text/plain")


# ── usage recording ────────────────────────────────────────────────────────────

def _record_research_usage(db: Session, user_id: uuid.UUID, report: str, latency_ms: int) -> None:
    try:
        from app.core.config import settings
        from app.services.usage_service import estimate_cost, record_usage
        o    = max(1, len(report) // 4)
        cost = estimate_cost(settings.LLM_MODEL, 500, o)
        record_usage(db, user_id, "research", 500 + o, cost)
    except Exception as exc:
        logger.warning("Research usage recording failed: %s", exc)
