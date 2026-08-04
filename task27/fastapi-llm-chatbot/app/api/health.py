"""Health and readiness endpoints.

/health is intentionally trivial and fast — it must never call the LLM or
do any I/O, since it is polled frequently by Docker and cloud health checks.

/ready checks that required configuration is present.
"""

from fastapi import APIRouter, Depends

from app.config.settings import Settings, get_settings
from app.models.schemas import HealthResponse, ReadyResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="healthy")


@router.get("/ready", response_model=ReadyResponse)
async def ready(settings: Settings = Depends(get_settings)) -> ReadyResponse:
    llm_ok = settings.llm_configured()
    return ReadyResponse(
        status="ready" if llm_ok else "not_ready",
        llm_configured=llm_ok,
    )
