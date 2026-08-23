"""Health check router — the first proven Streamlit -> FastAPI round trip."""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.schemas.health import HealthResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    logger.info("Health check requested")
    return HealthResponse(
        status="ok",
        app_name=settings.APP_NAME,
        environment=settings.APP_ENV,
    )


@router.get("/health/db")
def health_check_db(db: Session = Depends(get_db)) -> dict:
    """Verifies the app can actually reach PostgreSQL (Phase 3)."""
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "reachable"}
    except Exception as exc:  # pragma: no cover - depends on live DB
        logger.exception("Database health check failed")
        return {"status": "error", "database": "unreachable", "detail": str(exc)}
