"""
Centralized application settings using Pydantic BaseSettings.

All configuration is read from environment variables / .env file.
Import the singleton `settings` object instead of using os.getenv() directly.

Usage:
    from config.settings import settings
    print(settings.openai_api_key)
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application-wide settings loaded from environment variables.

    Pydantic validates every field at startup — the app fails fast
    with a clear error if a required variable is missing or has the
    wrong type.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",          # silently ignore unknown env vars
    )

    # ── Application ───────────────────────────────────────────────────────────
    app_title: str = Field(default="AI Research Assistant", description="Application display name")
    app_version: str = Field(default="1.0.0", description="Semantic version")

    # ── LLM Provider ──────────────────────────────────────────────────────────
    openai_api_key: str = Field(default="", description="OpenAI API key")
    google_api_key: str = Field(default="", description="Google Gemini API key")
    ollama_base_url: str = Field(
        default="http://localhost:11434",
        description="Base URL for local Ollama server",
    )

    default_llm_provider: Literal["openai", "gemini", "ollama"] = Field(
        default="openai",
        description="Which LLM provider to use by default",
    )
    default_model: str = Field(
        default="gpt-4o-mini",
        description="Default model name for the selected provider",
    )
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Sampling temperature for LLM responses",
    )
    max_tokens: int = Field(
        default=4096,
        gt=0,
        description="Maximum tokens per LLM response",
    )

    # ── Web Search ────────────────────────────────────────────────────────────
    tavily_api_key: str = Field(default="", description="Tavily Search API key")
    max_search_results: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of search results to retrieve per query",
    )
    search_depth: Literal["basic", "advanced"] = Field(
        default="advanced",
        description="Tavily search depth",
    )

    # ── LangSmith Tracing ─────────────────────────────────────────────────────
    langchain_tracing_v2: bool = Field(
        default=False,
        description="Enable LangSmith distributed tracing",
    )
    langchain_api_key: str = Field(default="", description="LangSmith API key")
    langchain_project: str = Field(
        default="multi-agent-research-assistant",
        description="LangSmith project name",
    )

    # ── Logging ───────────────────────────────────────────────────────────────
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Minimum log level to emit",
    )
    log_format: Literal["json", "console"] = Field(
        default="json",
        description="Log output format — json for production, console for dev",
    )

    # ── Agent Behaviour ───────────────────────────────────────────────────────
    max_retries: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum retry attempts for failed agent steps",
    )
    retry_delay: float = Field(
        default=1.0,
        ge=0.0,
        description="Base delay in seconds between retries (exponential backoff)",
    )

    # ── Validators ────────────────────────────────────────────────────────────
    @field_validator("temperature")
    @classmethod
    def validate_temperature(cls, v: float) -> float:
        """Ensure temperature is within OpenAI's accepted range."""
        if not 0.0 <= v <= 2.0:
            raise ValueError(f"temperature must be between 0.0 and 2.0, got {v}")
        return v

    # ── Convenience helpers ───────────────────────────────────────────────────
    @property
    def has_openai_key(self) -> bool:
        """Return True if a real OpenAI key is configured."""
        return bool(self.openai_api_key) and not self.openai_api_key.startswith("your-")

    @property
    def has_tavily_key(self) -> bool:
        """Return True if a real Tavily key is configured."""
        return bool(self.tavily_api_key) and not self.tavily_api_key.startswith("your-")

    @property
    def has_google_key(self) -> bool:
        """Return True if a real Google API key is configured."""
        return bool(self.google_api_key) and not self.google_api_key.startswith("your-")

    @property
    def langsmith_enabled(self) -> bool:
        """Return True if LangSmith tracing is fully configured."""
        return self.langchain_tracing_v2 and bool(self.langchain_api_key)

    def get_model_for_provider(self) -> str:
        """
        Return the appropriate model name based on the active provider.

        Falls back to a sensible default for each provider if the
        default_model field doesn't match the provider's naming convention.
        """
        provider_defaults = {
            "openai": "gpt-4o-mini",
            "gemini": "gemini-1.5-flash",
            "ollama": "llama3",
        }
        return self.default_model or provider_defaults.get(self.default_llm_provider, "gpt-4o-mini")

    def display_summary(self) -> dict:
        """Return a safe (no secrets) summary for display / logging."""
        return {
            "app_title": self.app_title,
            "app_version": self.app_version,
            "llm_provider": self.default_llm_provider,
            "model": self.get_model_for_provider(),
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "openai_configured": self.has_openai_key,
            "tavily_configured": self.has_tavily_key,
            "google_configured": self.has_google_key,
            "langsmith_enabled": self.langsmith_enabled,
            "log_level": self.log_level,
        }


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return the cached Settings singleton.

    Using lru_cache ensures the .env file is only parsed once,
    and the same object is shared across all imports.
    """
    return Settings()


# Module-level singleton — import this directly
settings: Settings = get_settings()
