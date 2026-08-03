"""Application settings and environment management."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """Typed application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = Field(default="Secure AI Assistant", alias="APP_NAME")
    environment: str = Field(default="development", alias="APP_ENV")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    logs_dir: str = Field(default="logs", alias="LOGS_DIR")

    assistant_scope: str = Field(
        default="General knowledge assistance with safety restrictions.",
        alias="ASSISTANT_SCOPE",
    )

    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_chat_model: str = Field(default="gpt-4.1-mini", alias="OPENAI_CHAT_MODEL")
    fallback_local_model: str = Field(default="", alias="FALLBACK_LOCAL_MODEL")

    input_guardrail_enabled: bool = Field(default=True, alias="INPUT_GUARDRAIL_ENABLED")
    output_guardrail_enabled: bool = Field(default=True, alias="OUTPUT_GUARDRAIL_ENABLED")
    block_off_topic: bool = Field(default=True, alias="BLOCK_OFF_TOPIC")
    max_prompt_length: int = Field(default=4000, alias="MAX_PROMPT_LENGTH")

    exports_dir: str = Field(default="exports", alias="EXPORTS_DIR")

    @property
    def logs_path(self) -> Path:
        """Return filesystem path where logs are written."""
        return Path(self.logs_dir).resolve()

    @property
    def exports_path(self) -> Path:
        """Return filesystem path where generated exports are written."""
        return Path(self.exports_dir).resolve()


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    """Return cached settings instance."""
    return AppSettings()
