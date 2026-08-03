"""
config/settings.py
==================
Central application settings loaded from environment variables via pydantic-settings.
Supports both Groq (primary) and OpenAI (fallback) providers.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# ---------------------------------------------------------------------------
# Base directory
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """
    Application-wide settings.
    Values are loaded from the .env file located at the project root.
    """

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ------------------------------------------------------------------
    # Groq (primary provider)
    # ------------------------------------------------------------------
    groq_api_key: str = Field(
        default="",
        description="Groq API key (gsk_...)",
    )

    # ------------------------------------------------------------------
    # OpenAI (optional fallback)
    # ------------------------------------------------------------------
    openai_api_key: str = Field(
        default="",
        description="OpenAI API key (sk-...)",
    )

    # ------------------------------------------------------------------
    # Model selection
    # ------------------------------------------------------------------
    default_model: str = Field(
        default="meta-llama/llama-4-scout-17b-16e-instruct",
        description="Primary vision model",
    )
    fallback_model: str = Field(
        default="llama-3.2-11b-vision-preview",
        description="Fallback model when primary is unavailable",
    )

    # ------------------------------------------------------------------
    # Application metadata
    # ------------------------------------------------------------------
    app_title: str = Field(default="Vision AI Assistant")
    app_version: str = Field(default="1.0.0")
    debug: bool = Field(default=False)

    # ------------------------------------------------------------------
    # Generation parameters
    # ------------------------------------------------------------------
    max_tokens: int = Field(default=4096, ge=256, le=16000)
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)

    # ------------------------------------------------------------------
    # Upload limits
    # ------------------------------------------------------------------
    max_image_size_mb: int = Field(default=20, ge=1, le=50)

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------
    export_dir: str = Field(default="exports")

    # ------------------------------------------------------------------
    # Computed helpers
    # ------------------------------------------------------------------
    @property
    def max_image_size_bytes(self) -> int:
        return self.max_image_size_mb * 1024 * 1024

    @property
    def export_path(self) -> Path:
        p = BASE_DIR / self.export_dir
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def groq_key_configured(self) -> bool:
        """True when a valid Groq key is present."""
        key = self.groq_api_key.strip()
        return bool(key) and key.startswith("gsk_") and "your" not in key

    @property
    def openai_key_configured(self) -> bool:
        """True when a valid OpenAI key is present."""
        key = self.openai_api_key.strip()
        return bool(key) and key.startswith("sk-") and "your" not in key

    @property
    def api_key_configured(self) -> bool:
        """True when at least one provider key is configured."""
        return self.groq_key_configured or self.openai_key_configured

    @property
    def active_provider(self) -> str:
        """Return 'groq' or 'openai' based on which key is available."""
        if self.groq_key_configured:
            return "groq"
        if self.openai_key_configured:
            return "openai"
        return "none"

    # ------------------------------------------------------------------
    # Validators
    # ------------------------------------------------------------------
    @field_validator("temperature")
    @classmethod
    def clamp_temperature(cls, v: float) -> float:
        return round(max(0.0, min(2.0, v)), 2)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the singleton Settings instance."""
    return Settings()
