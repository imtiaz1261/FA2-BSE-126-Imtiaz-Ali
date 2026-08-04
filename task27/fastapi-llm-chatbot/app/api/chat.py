"""Chat endpoint."""

import time

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.config.settings import Settings, get_settings
from app.models.schemas import ChatRequest, ChatResponse, ErrorResponse
from app.services.llm_service import (
    LLMNotConfiguredError,
    LLMProviderError,
    LLMRateLimitError,
    LLMService,
    LLMTimeoutError,
)
from app.utils.logging import get_logger
from app.utils.metrics import LLM_ERRORS_TOTAL, LLM_REQUEST_DURATION_SECONDS, LLM_REQUESTS_TOTAL

logger = get_logger("app.api.chat")

router = APIRouter(tags=["chat"])


def get_llm_service(settings: Settings = Depends(get_settings)) -> LLMService:
    return LLMService(settings)


@router.post(
    "/chat",
    response_model=ChatResponse,
    responses={
        400: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
        504: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def chat(
    payload: ChatRequest,
    settings: Settings = Depends(get_settings),
    llm_service: LLMService = Depends(get_llm_service),
) -> ChatResponse:
    if len(payload.message) > settings.max_message_length:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"message exceeds maximum length of {settings.max_message_length} characters",
        )

    provider = settings.llm_provider
    start = time.perf_counter()
    try:
        response_text = await llm_service.get_response(payload.message)
    except LLMNotConfiguredError:
        LLM_ERRORS_TOTAL.labels(provider=provider, error_type="not_configured").inc()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Chat service is not configured. Please contact the administrator.",
        )
    except LLMTimeoutError:
        LLM_ERRORS_TOTAL.labels(provider=provider, error_type="timeout").inc()
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Unable to process your request at this time.",
        )
    except LLMRateLimitError:
        LLM_ERRORS_TOTAL.labels(provider=provider, error_type="rate_limit").inc()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The chat service is temporarily busy. Please try again shortly.",
        )
    except LLMProviderError:
        LLM_ERRORS_TOTAL.labels(provider=provider, error_type="provider_error").inc()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to process your request at this time.",
        )
    except Exception:
        logger.exception("Unexpected error while calling LLM service")
        LLM_ERRORS_TOTAL.labels(provider=provider, error_type="unknown").inc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to process your request at this time.",
        )
    finally:
        LLM_REQUEST_DURATION_SECONDS.labels(provider=provider).observe(time.perf_counter() - start)

    LLM_REQUESTS_TOTAL.labels(provider=provider, status="success").inc()

    return ChatResponse(
        response=response_text,
        model=settings.default_model,
        provider=provider,
    )
