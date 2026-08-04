"""
LLM service.

Talks to the configured LLM provider using the OpenAI-compatible chat
completions REST API (both Groq and OpenAI implement this shape), so the
same client code works for either provider by just swapping the base URL,
API key, and model.
"""

import time
from typing import Optional

import httpx

from app.config.settings import Settings
from app.utils.logging import get_logger

logger = get_logger("app.services.llm_service")

PROVIDER_BASE_URLS = {
    "groq": "https://api.groq.com/openai/v1",
    "openai": "https://api.openai.com/v1",
}


class LLMServiceError(Exception):
    """Base class for LLM service errors."""


class LLMNotConfiguredError(LLMServiceError):
    """Raised when no API key is configured for the active provider."""


class LLMTimeoutError(LLMServiceError):
    """Raised when the LLM provider does not respond in time."""


class LLMRateLimitError(LLMServiceError):
    """Raised when the LLM provider returns a rate-limit response."""


class LLMProviderError(LLMServiceError):
    """Raised for any other non-2xx response from the provider."""


class LLMService:
    def __init__(self, settings: Settings):
        self._settings = settings
        self._base_url = PROVIDER_BASE_URLS.get(settings.llm_provider)
        if self._base_url is None:
            logger.warning(
                "Unknown LLM provider configured, defaulting to Groq base URL",
                extra={"llm_provider": settings.llm_provider},
            )
            self._base_url = PROVIDER_BASE_URLS["groq"]

    async def get_response(self, message: str) -> str:
        api_key = self._settings.active_api_key()
        if not api_key:
            raise LLMNotConfiguredError(
                f"No API key configured for provider '{self._settings.llm_provider}'"
            )

        model = self._settings.default_model
        url = f"{self._base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": model,
            "messages": [{"role": "user", "content": message}],
            "temperature": 0.7,
        }

        start = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=self._settings.llm_timeout_seconds) as client:
                resp = await client.post(url, headers=headers, json=body)
        except httpx.TimeoutException as exc:
            logger.error(
                "LLM request timed out",
                extra={"provider": self._settings.llm_provider, "model": model},
            )
            raise LLMTimeoutError("The LLM provider took too long to respond") from exc
        except httpx.RequestError as exc:
            logger.error(
                "LLM request network error",
                extra={"provider": self._settings.llm_provider, "error_type": type(exc).__name__},
            )
            raise LLMProviderError("Network error while contacting the LLM provider") from exc

        elapsed = time.perf_counter() - start

        if resp.status_code == 429:
            logger.warning(
                "LLM provider rate limit hit",
                extra={"provider": self._settings.llm_provider, "duration_seconds": round(elapsed, 3)},
            )
            raise LLMRateLimitError("Rate limit exceeded on the LLM provider")

        if resp.status_code >= 400:
            # Never log the request/response body — it may contain the key or user content.
            logger.error(
                "LLM provider returned an error status",
                extra={
                    "provider": self._settings.llm_provider,
                    "status_code": resp.status_code,
                    "duration_seconds": round(elapsed, 3),
                },
            )
            raise LLMProviderError(f"LLM provider returned status {resp.status_code}")

        try:
            data = resp.json()
            content: Optional[str] = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, ValueError) as exc:
            logger.error("Unexpected LLM response shape", extra={"provider": self._settings.llm_provider})
            raise LLMProviderError("Unexpected response shape from LLM provider") from exc

        logger.info(
            "LLM request completed",
            extra={
                "provider": self._settings.llm_provider,
                "model": model,
                "duration_seconds": round(elapsed, 3),
            },
        )
        return content or ""
