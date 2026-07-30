"""config/settings.py — Centralized, validated application configuration.

Every other module reads configuration from here, never directly from
os.environ — this means all settings are validated once, at startup, in
one place, instead of scattered environment-variable lookups (and
potential typos) throughout the codebase.

Uses pydantic-settings, which automatically:
  1. Reads values from environment variables / a .env file
  2. Validates their types (e.g. WORD_COUNT_DEFAULT must be an int)
  3. Raises a clear error immediately at startup if something required
     is missing, rather than failing deep inside an agent call later
"""

from __future__ import annotations

from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- LLM provider (Groq — free, OpenAI-compatible API) ---
    groq_api_key: str = Field(..., description="Groq API key, from console.groq.com/keys")
    llm_model_name: str = Field(default="llama-3.3-70b-versatile")
    llm_base_url: str = Field(default="https://api.groq.com/openai/v1")

    # --- Web search tool ---
    search_max_results: int = Field(default=5, ge=1, le=20)

    # --- Content generation defaults ---
    default_word_count: int = Field(default=800, ge=100, le=10000)
    default_tone: str = Field(default="professional")

    # --- Output paths ---
    output_dir: Path = Field(default=PROJECT_ROOT / "output")
    logs_dir: Path = Field(default=PROJECT_ROOT / "logs")

    @field_validator("groq_api_key")
    @classmethod
    def validate_api_key_not_placeholder(cls, value: str) -> str:
        """Catches the common mistake of leaving the .env.example
        placeholder text in place, failing fast with a clear message
        instead of a confusing 401 error from Groq later."""
        if not value or "your_api_key_here" in value:
            raise ValueError(
                "GROQ_API_KEY is missing or still set to the placeholder value. "
                "Get a free key at https://console.groq.com/keys and set it "
                "in your .env file."
            )
        return value


def get_settings() -> Settings:
    """Factory function (rather than a bare module-level instance) so
    tests can construct Settings with overridden values without needing
    real environment variables set."""
    settings = Settings()
    settings.output_dir.mkdir(parents=True, exist_ok=True)
    settings.logs_dir.mkdir(parents=True, exist_ok=True)
    return settings
