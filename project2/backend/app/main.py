"""
FastAPI application entrypoint — Phases 1–15.

Routers registered:
  /api/health          — Phase 2
  /api/auth            — Phase 4
  /api/conversations   — Phase 5
  /api/messages        — Phase 6/7/9/10/11/14/15
  /api/documents       — Phase 8
  /api/.../agent       — Phase 11/12
  /api/research        — Phase 13
  /api/subscription    — Phase 15
  /api/usage           — Phase 15
  /api/admin           — Phase 18
"""

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import admin, agent, auth, conversations, documents, health, messages
from app.api.research import router as research_router
from app.api.subscription import subscription_router, usage_router
from app.core.config import settings
from app.core.logging_config import configure_logging

configure_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.APP_NAME,
    description="AI Research & Knowledge Workspace — production-grade SaaS platform.",
    version="1.0.0",
    debug=settings.DEBUG,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Core
app.include_router(health.router,           prefix=settings.API_V1_PREFIX)
app.include_router(auth.router,             prefix=settings.API_V1_PREFIX)
app.include_router(conversations.router,    prefix=settings.API_V1_PREFIX)
app.include_router(messages.router,         prefix=settings.API_V1_PREFIX)
app.include_router(documents.router,        prefix=settings.API_V1_PREFIX)
# Agent
app.include_router(agent.router,            prefix=settings.API_V1_PREFIX)
# Phase 13 — Research
app.include_router(research_router,         prefix=settings.API_V1_PREFIX)
# Phase 15 — Subscription + Usage
app.include_router(subscription_router,     prefix=settings.API_V1_PREFIX)
app.include_router(usage_router,            prefix=settings.API_V1_PREFIX)
# Phase 18 — Admin
app.include_router(admin.router,            prefix=settings.API_V1_PREFIX)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Please try again."},
    )


@app.on_event("startup")
async def on_startup() -> None:
    logger.info(
        "%s starting up in '%s' mode | guardrails=%s",
        settings.APP_NAME,
        settings.APP_ENV,
        settings.GUARDRAILS_ENABLED,
    )
