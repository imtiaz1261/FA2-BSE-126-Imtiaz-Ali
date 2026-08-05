"""
Centralized Streamlit-side configuration.

Loads from the SAME single root-level `.env` file the backend uses
(see `.env.example` at the project root). Path resolved relative to
this file's location so it works from any cwd.
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# frontend/streamlit_app/config.py -> project root is 2 levels up
PROJECT_ROOT = Path(__file__).resolve().parents[2]
ROOT_ENV_FILE = PROJECT_ROOT / ".env"


class FrontendSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ROOT_ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    API_BASE_URL: str = "http://localhost:8000/api"
    APP_TITLE: str = "AI Research & Knowledge Workspace"


@lru_cache
def get_settings() -> FrontendSettings:
    return FrontendSettings()


settings = get_settings()
