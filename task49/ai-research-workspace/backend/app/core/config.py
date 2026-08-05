"""
Centralized application configuration.

Loads from a SINGLE root-level `.env` file shared by both the backend
and the frontend (see `.env.example` at the project root). The path
is resolved relative to this file's location, not the current working
directory, so it works whether you run uvicorn from `backend/` or
from the project root.

Every later phase (auth, RAG, agents, guardrails, SaaS usage, Redis,
Langfuse, etc.) reads its settings from this one `Settings` object
instead of calling `os.environ` directly.
"""

from functools import lru_cache
from pathlib import Path
from typing import List, Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/core/config.py -> project root is 3 levels up
PROJECT_ROOT = Path(__file__).resolve().parents[3]
ROOT_ENV_FILE = PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ROOT_ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---------------------------------------------------------------
    # General / App
    # ---------------------------------------------------------------
    APP_NAME: str = "AI Research & Knowledge Workspace"
    APP_ENV: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api"
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # CORS — Streamlit runs on a different port than FastAPI locally
    CORS_ORIGINS: List[str] = ["http://localhost:8501", "http://127.0.0.1:8501"]

    # ---------------------------------------------------------------
    # Database (Phase 3)
    # ---------------------------------------------------------------
    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/ai_workspace"
    DB_ECHO: bool = False

    # ---------------------------------------------------------------
    # Auth / JWT (Phase 4)
    # ---------------------------------------------------------------
    JWT_SECRET_KEY: str = "change-me-in-env"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day

    # ---------------------------------------------------------------
    # LLM Provider (Phase 6)
    # ---------------------------------------------------------------
    LLM_PROVIDER: Literal["openai", "groq", "local"] = "openai"
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_TEMPERATURE: float = 0.3

    # ---------------------------------------------------------------
    # Embeddings / Vector store (Phase 9-10)
    # ---------------------------------------------------------------
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    VECTOR_DIM: int = 1536
    CHUNK_SIZE: int = 800
    CHUNK_OVERLAP: int = 120

    # ---------------------------------------------------------------
    # Web Search / Research tool (Phase 12-13)
    # ---------------------------------------------------------------
    WEB_SEARCH_API_KEY: str = ""

    # ---------------------------------------------------------------
    # Redis (Phase 16)
    # ---------------------------------------------------------------
    REDIS_URL: str = "redis://localhost:6379/0"
    RATE_LIMIT_PER_MINUTE: int = 60

    # ---------------------------------------------------------------
    # Langfuse Observability (Phase 17)
    # ---------------------------------------------------------------
    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_SECRET_KEY: str = ""
    LANGFUSE_HOST: str = "https://cloud.langfuse.com"

    # ---------------------------------------------------------------
    # SaaS Plans / Usage (Phase 15)
    # ---------------------------------------------------------------
    FREE_PLAN_DAILY_MESSAGE_LIMIT: int = 20
    PRO_PLAN_DAILY_MESSAGE_LIMIT: int = 500

    # ---------------------------------------------------------------
    # Logging
    # ---------------------------------------------------------------
    LOG_LEVEL: str = Field(default="INFO")


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (singleton for the process)."""
    return Settings()


settings = get_settings()
