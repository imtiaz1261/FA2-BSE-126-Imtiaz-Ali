"""
Application configuration.

All configuration is loaded from environment variables (or a local .env file
during development). Nothing here should ever contain a real secret value —
secrets belong in your local .env file or your cloud platform's environment
variable manager, never in source code.
"""

from functools import lru_cache
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- General ---
    app_name: str = Field(default="LLM Chatbot")
    app_version: str = Field(default="1.0.0")
    environment: str = Field(default="development")  # development | production

    # --- Server ---
    host: str = Field(default="0.0.0.0")
    # Cloud platforms (Railway/Render) inject PORT at runtime.
    port: int = Field(default=8000)

    # --- LLM ---
    llm_provider: str = Field(default="groq")  # groq | openai
    llm_model: str = Field(default="")
    llm_timeout_seconds: float = Field(default=30.0)

    groq_api_key: Optional[str] = Field(default=None)
    openai_api_key: Optional[str] = Field(default=None)

    # --- Logging ---
    log_level: str = Field(default="INFO")

    # --- Security / CORS ---
    cors_allow_origins: str = Field(default="*")  # comma-separated list
    max_message_length: int = Field(default=4000)

    @field_validator("environment")
    @classmethod
    def _normalize_environment(cls, v: str) -> str:
        v = (v or "development").lower()
        if v not in {"development", "production"}:
            return "development"
        return v

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def cors_origins_list(self) -> List[str]:
        raw = (self.cors_allow_origins or "*").strip()
        if raw == "*":
            return ["*"]
        return [origin.strip() for origin in raw.split(",") if origin.strip()]

    @property
    def default_model(self) -> str:
        """Resolve a sensible default model per provider if none was set."""
        if self.llm_model:
            return self.llm_model
        if self.llm_provider == "groq":
            return "llama-3.1-8b-instant"
        if self.llm_provider == "openai":
            return "gpt-4o-mini"
        return "llama-3.1-8b-instant"

    def active_api_key(self) -> Optional[str]:
        if self.llm_provider == "groq":
            return self.groq_api_key
        if self.llm_provider == "openai":
            return self.openai_api_key
        return None

    def llm_configured(self) -> bool:
        return bool(self.active_api_key())


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance — env vars are read once per process."""
    return Settings()
