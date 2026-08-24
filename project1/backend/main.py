"""
backend/main.py — FastAPI Application Entry Point
===================================================
Responsibilities (and only these):
    1. Create the FastAPI app instance
    2. Register middleware
    3. Include routers
    4. Manage startup / shutdown lifecycle

All business logic lives in services/.
All database logic lives in db/.
All AI logic lives in ai/.

This file stays thin on purpose.
"""

import time
from contextlib import asynccontextmanager
from typing import Any

import redis.asyncio as aioredis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.core.config import settings
from backend.core.logging import configure_logging, get_logger
from backend.db.session import check_db_connection
from backend.db.seeder import run_seeder
from backend.core.exceptions import register_exception_handlers

# ---------------------------------------------------------------------------
# Route imports
# ---------------------------------------------------------------------------
from backend.api.v1.routes.auth import router as auth_router
from backend.api.v1.routes.chat import router as chat_router
from backend.api.v1.routes.documents import router as documents_router
from backend.api.v1.routes.subscriptions import router as subscriptions_router
from backend.api.v1.routes.admin import router as admin_router

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Redis client (module-level, shared across requests)
# ---------------------------------------------------------------------------
# Created once at startup, closed at shutdown.
# Stored as a module-level variable so the health check and future
# middleware can access it without dependency injection overhead.
_redis_client: aioredis.Redis | None = None


async def get_redis_client() -> aioredis.Redis:
    """
    Return the shared Redis client.
    Raises RuntimeError if called before startup completes.
    """
    if _redis_client is None:
        raise RuntimeError("Redis client not initialised — startup incomplete")
    return _redis_client


async def check_redis_connection() -> bool:
    """
    Verify Redis is reachable by sending a PING command.

    Returns:
        True if Redis responds, False otherwise.
    """
    try:
        client = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=5,
        )
        await client.ping()
        await client.aclose()
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Lifespan — startup and shutdown
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager.

    Everything before `yield` runs at startup.
    Everything after `yield` runs at shutdown.

    Startup sequence:
        1. Configure structured logging
        2. Verify PostgreSQL is reachable
        3. Verify Redis is reachable
        4. Initialise the shared Redis client
        5. Run the database seeder (idempotent)
        6. Log "ready" message

    Shutdown sequence:
        1. Close the Redis connection pool
        2. Log "shutdown" message
    """
    global _redis_client

    # ------------------------------------------------------------------
    # 1. Configure logging first — everything after this produces
    #    structured JSON logs (or coloured dev output).
    # ------------------------------------------------------------------
    configure_logging()

    logger.info(
        "aihub_starting",
        app=settings.APP_NAME,
        version=settings.APP_VERSION,
        env=settings.APP_ENV,
        debug=settings.DEBUG,
    )

    # ------------------------------------------------------------------
    # 2. PostgreSQL health check
    # ------------------------------------------------------------------
    logger.info("startup_checking_database")
    db_ok = await check_db_connection()

    if not db_ok:
        logger.error(
            "startup_database_unreachable",
            host=settings.POSTGRES_HOST,
            port=settings.POSTGRES_PORT,
            db=settings.POSTGRES_DB,
        )
        # In production, you might want to raise here to prevent the
        # app from starting with no database.  In development, we
        # continue so you can at least inspect the API docs.
        if settings.APP_ENV == "production":
            raise RuntimeError(
                f"Cannot connect to PostgreSQL at "
                f"{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}"
            )
        logger.warning("startup_continuing_without_database_dev_mode_only")
    else:
        logger.info(
            "startup_database_connected",
            host=settings.POSTGRES_HOST,
            port=settings.POSTGRES_PORT,
        )

    # ------------------------------------------------------------------
    # 3. Redis health check
    # ------------------------------------------------------------------
    logger.info("startup_checking_redis")
    redis_ok = await check_redis_connection()

    if not redis_ok:
        logger.error(
            "startup_redis_unreachable",
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
        )
        if settings.APP_ENV == "production":
            raise RuntimeError(
                f"Cannot connect to Redis at "
                f"{settings.REDIS_HOST}:{settings.REDIS_PORT}"
            )
        logger.warning("startup_continuing_without_redis_dev_mode_only")
    else:
        logger.info(
            "startup_redis_connected",
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
        )

    # ------------------------------------------------------------------
    # 4. Initialise shared Redis client
    # ------------------------------------------------------------------
    if redis_ok:
        _redis_client = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            max_connections=20,
        )
        logger.info("startup_redis_client_initialised")

    # ------------------------------------------------------------------
    # 5. Run database seeder
    # ------------------------------------------------------------------
    if db_ok:
        try:
            logger.info("startup_running_seeder")
            await run_seeder()
        except Exception as exc:
            # Seeder failure is not fatal — the app can still serve
            # requests.  Log the error for investigation.
            logger.error(
                "startup_seeder_failed",
                error=str(exc),
                exc_info=True,
            )

    # ------------------------------------------------------------------
    # 6. Application ready
    # ------------------------------------------------------------------
    logger.info(
        "aihub_ready",
        docs_url=f"{settings.BACKEND_URL}/docs" if settings.DEBUG else "disabled",
        db_connected=db_ok,
        redis_connected=redis_ok,
    )

    # ── yield — application serves requests ──────────────────────────
    yield
    # ─────────────────────────────────────────────────────────────────

    # ------------------------------------------------------------------
    # Shutdown
    # ------------------------------------------------------------------
    logger.info("aihub_shutting_down")

    if _redis_client is not None:
        await _redis_client.aclose()
        logger.info("startup_redis_client_closed")

    logger.info("aihub_shutdown_complete")


# ---------------------------------------------------------------------------
# Application Factory
# ---------------------------------------------------------------------------

def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Using a factory function (not a bare module-level `app = FastAPI()`)
    means tests can call `create_app()` with different settings to get
    an isolated instance — no shared state between test cases.
    """
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=(
            "AIHub — Intelligent AI SaaS Platform\n\n"
            "Features: RAG · AI Agents · Tool Calling · Streaming · "
            "Subscriptions · Usage Limits · Guardrails"
        ),
        # Only expose interactive docs in non-production environments
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        openapi_url="/openapi.json" if settings.DEBUG else None,
        lifespan=lifespan,
    )

    # Register global exception handlers (JSON responses & structured logs)
    register_exception_handlers(app)

    # ------------------------------------------------------------------
    # Middleware
    # ------------------------------------------------------------------

    # CORS — allows the Streamlit frontend (port 8501) to call the API
    # (port 8000) without the browser blocking the request.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    # ------------------------------------------------------------------
    # Routers
    # ------------------------------------------------------------------
    API_PREFIX = "/api/v1"

    app.include_router(auth_router,          prefix=API_PREFIX)
    app.include_router(chat_router,          prefix=API_PREFIX)
    app.include_router(documents_router,     prefix=API_PREFIX)
    app.include_router(subscriptions_router, prefix=API_PREFIX)
    app.include_router(admin_router,         prefix=API_PREFIX)

    # ------------------------------------------------------------------
    # Root endpoints
    # ------------------------------------------------------------------

    @app.get("/", tags=["Root"], include_in_schema=False)
    async def root() -> dict[str, Any]:
        """API root — confirms the service is running."""
        return {
            "app": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "status": "running",
            "environment": settings.APP_ENV,
            "docs": "/docs" if settings.DEBUG else None,
        }

    @app.get("/health", tags=["Health"])
    async def health() -> JSONResponse:
        """
        Detailed health check endpoint.

        Tests real connectivity to PostgreSQL and Redis.
        Returns 200 when healthy, 503 when any dependency is down.

        Used by:
        - Docker HEALTHCHECK directive
        - Load balancer health probes
        - Kubernetes liveness/readiness probes
        - Monitoring dashboards

        Response structure:
            {
                "status": "healthy" | "degraded" | "unhealthy",
                "version": "0.1.0",
                "checks": {
                    "database": {"status": "ok", "latency_ms": 4},
                    "redis":    {"status": "ok", "latency_ms": 1}
                }
            }
        """
        checks: dict[str, Any] = {}
        overall_healthy = True

        # Check database
        t0 = time.monotonic()
        db_ok = await check_db_connection()
        db_latency = round((time.monotonic() - t0) * 1000, 2)
        checks["database"] = {
            "status": "ok" if db_ok else "error",
            "latency_ms": db_latency,
        }
        if not db_ok:
            overall_healthy = False

        # Check Redis
        t0 = time.monotonic()
        redis_ok = await check_redis_connection()
        redis_latency = round((time.monotonic() - t0) * 1000, 2)
        checks["redis"] = {
            "status": "ok" if redis_ok else "error",
            "latency_ms": redis_latency,
        }
        if not redis_ok:
            overall_healthy = False

        status_code = 200 if overall_healthy else 503
        status_text = "healthy" if overall_healthy else "unhealthy"

        return JSONResponse(
            status_code=status_code,
            content={
                "status": status_text,
                "version": settings.APP_VERSION,
                "environment": settings.APP_ENV,
                "checks": checks,
            },
        )

    return app


# ---------------------------------------------------------------------------
# Application instance
# ---------------------------------------------------------------------------
app = create_app()
