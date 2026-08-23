"""
App entrypoint. Run with:
    uvicorn app.main:app --reload
"""
import logging
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.middleware.sessions import SessionMiddleware

from app.config import settings
from app.database import Base, engine, get_db
from app.dependencies import limiter
from app.logging_config import setup_logging
from app.routers import (
    agent,
    auth,
    billing,
    chat,
    conversations,
    documents,
    memory,
    oauth,
    share,
    settings as settings_router,
    vision,
)
from app.routers import (
    admin_analytics,
    admin_billing,
    admin_moderation,
    admin_users,
)
from app.sentry_init import init_sentry

# Setup logging first
setup_logging()

# Initialize Sentry for error tracking
init_sentry()

logger = logging.getLogger(__name__)

app = FastAPI(title=settings.app_name, version="0.1.0")

# Required by Authlib to store the OAuth `state` param between redirect and
# callback. Uses the same secret as JWT signing for simplicity; feel free to
# split these in production.
app.add_middleware(SessionMiddleware, secret_key=settings.jwt_secret_key)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.frontend_url,
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,  # required so the refresh-token cookie is sent
    allow_methods=["*"],
    allow_headers=["*"],
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# Register all routers
app.include_router(auth.router)
app.include_router(oauth.router)
app.include_router(chat.router)
app.include_router(conversations.router)
app.include_router(conversations.folders_router)
app.include_router(share.router)
app.include_router(settings_router.router)
app.include_router(settings_router.models_router)
app.include_router(settings_router.usage_router)
app.include_router(settings_router.conversations_router, prefix="/conversations")
app.include_router(documents.router)
app.include_router(vision.router)
app.include_router(agent.router)
app.include_router(memory.router)
app.include_router(billing.router)

# Admin routes
app.include_router(admin_analytics.router)
app.include_router(admin_users.router)
app.include_router(admin_billing.router)
app.include_router(admin_moderation.router)


# ============================================================================
# Health Check Endpoints
# ============================================================================


@app.get("/health")
async def health_check():
    """
    Health check endpoint.

    Returns 200 if the application process is alive.
    Used by Docker health checks, load balancers, and Kubernetes liveness probes.

    Response:
        {"status": "healthy", "service": "backend"}
    """
    return {"status": "healthy", "service": "backend"}


@app.get("/ready")
async def readiness_check(db: AsyncSession = Depends(get_db)):
    """
    Readiness check endpoint.

    Returns 200 only if critical dependencies are available:
    - Database connection
    - Required configuration

    Returns 503 if any critical dependency is unavailable.
    Used by Kubernetes readiness probes to determine if traffic should be routed.

    Response:
        {
            "status": "ready",
            "service": "backend",
            "database": "connected",
            "timestamp": "2026-08-16T12:00:00+00:00"
        }
    """
    try:
        # Check database
        await db.execute(text("SELECT 1"))

        return {
            "status": "ready",
            "service": "backend",
            "database": "connected",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"Readiness check failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "Service not ready", "reason": str(e)},
        )


@app.get("/metrics")
async def metrics():
    """
    Prometheus metrics endpoint.

    Returns metrics in Prometheus text format.
    Scraped by Prometheus for monitoring and alerting.
    """
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    from prometheus_client.openmetrics.exposition import generate_latest as openmetrics_generate_latest

    # Use OpenMetrics format (preferred)
    metrics_data = openmetrics_generate_latest()

    return metrics_data


# ============================================================================
# Startup / Shutdown
# ============================================================================


@app.on_event("startup")
async def on_startup():
    """Application startup event handler."""
    logger.info(f"Starting {settings.app_name} (environment: {settings.environment})")

    # For local development only. In production, manage schema changes with
    # Alembic migrations instead of create_all (see README).
    if not settings.is_production:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Created database tables (development mode)")


@app.on_event("shutdown")
async def on_shutdown():
    """Application shutdown event handler."""
    logger.info(f"Shutting down {settings.app_name}")
    await engine.dispose()
