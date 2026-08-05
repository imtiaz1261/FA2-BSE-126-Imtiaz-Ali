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
BACKEND_DIR = Path(__file__).resolve().parents[2]


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
    LLM_MAX_HISTORY_MESSAGES: int = 20
    LLM_SYSTEM_PROMPT: str = (
        "You are a helpful, precise AI research assistant. "
        "Answer clearly and concisely, and say when you're not sure."
    )

    # ---------------------------------------------------------------
    # Document storage (Phase 8)
    # ---------------------------------------------------------------
    STORAGE_DIR: str = "storage/documents"
    MAX_UPLOAD_SIZE_MB: int = 20
    ALLOWED_DOCUMENT_CONTENT_TYPES: List[str] = [
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain",
        "text/markdown",
    ]

    # ---------------------------------------------------------------
    # Embeddings / Vector store (Phase 9-10)
    # ---------------------------------------------------------------
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_API_KEY: str = ""      # defaults to OPENAI_API_KEY if blank
    EMBEDDING_BASE_URL: str = "https://api.openai.com/v1"  # always OpenAI for embeddings
    VECTOR_DIM: int = 1536
    CHUNK_SIZE: int = 800
    CHUNK_OVERLAP: int = 120

    # ---------------------------------------------------------------
    # Web Search / Research tool (Phase 12-13)
    # ---------------------------------------------------------------
    WEB_SEARCH_API_KEY: str = ""
    TAVILY_API_KEY: str = ""          # Tavily search API key (Phase 12)

    # ---------------------------------------------------------------
    # Agent (Phase 11-12)
    # ---------------------------------------------------------------
    AGENT_MAX_ITERATIONS: int = 8     # max tool-call rounds before forced stop
    AGENT_TIMEOUT_SECONDS: int = 60   # hard wall-clock limit per agent run

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
    # Phase 13: Deep Web Research
    # ---------------------------------------------------------------
    RESEARCH_MAX_QUERIES: int = 5          # parallel search queries per research run
    RESEARCH_MAX_SOURCES: int = 15         # sources to process per run
    RESEARCH_TIMEOUT_SECONDS: int = 120    # hard timeout for a full research run

    # ---------------------------------------------------------------
    # Phase 14: Guardrails & AI Security
    # ---------------------------------------------------------------
    GUARDRAILS_ENABLED: bool = True
    GUARDRAIL_LLM_CHECK: bool = True       # use LLM for nuanced injection detection
    GUARDRAIL_BLOCK_THRESHOLD: float = 0.7 # classifier score above which to block
    MAX_INPUT_LENGTH: int = 8000           # chars; longer inputs are truncated

    # ---------------------------------------------------------------
    # Phase 15: SaaS Plans / Usage / Stripe
    # ---------------------------------------------------------------
    # Monthly request quotas per plan
    FREE_PLAN_MONTHLY_LIMIT: int = 100
    PRO_PLAN_MONTHLY_LIMIT: int = 2000
    ENTERPRISE_PLAN_MONTHLY_LIMIT: int = 50000

    # Document upload limits per plan
    FREE_PLAN_MAX_DOCS: int = 5
    PRO_PLAN_MAX_DOCS: int = 100
    ENTERPRISE_PLAN_MAX_DOCS: int = 1000

    # Stripe (test mode)
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_PRO_PRICE_ID: str = ""
    STRIPE_ENTERPRISE_PRICE_ID: str = ""

    # Legacy daily limits (kept for back-compat)
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
