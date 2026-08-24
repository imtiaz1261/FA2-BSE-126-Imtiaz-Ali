"""
core/config.py — Centralised Application Settings
===================================================
All configuration is read from environment variables (or the .env
file via pydantic-settings).  Nothing is hard-coded here.

Why pydantic-settings?
- Automatic type coercion  (e.g. "true" → True, "30" → int)
- Validation at startup — the app fails fast with a clear error
  message if a required variable is missing, rather than crashing
  at runtime deep inside a request handler.
- A single source of truth for every setting in the application.

Usage anywhere in the codebase:
    from backend.core.config import settings
    print(settings.OPENAI_MODEL)
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import PostgresDsn, RedisDsn, field_validator
from typing import List


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables / .env file.
    All fields have types — pydantic will raise a ValidationError on startup
    if any required value is missing or has the wrong type.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",        # Silently ignore unknown env vars
    )

    # ------------------------------------------------------------------
    # Application
    # ------------------------------------------------------------------
    APP_NAME: str = "AIHub"
    APP_ENV: str = "development"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True
    SECRET_KEY: str
    ALLOWED_ORIGINS: str = "http://localhost:8501"

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_origins(cls, v: str) -> str:
        return v  # Kept as string; parsed to list in property below

    @property
    def allowed_origins_list(self) -> List[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",")]

    # ------------------------------------------------------------------
    # Database
    # ------------------------------------------------------------------
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "aihub"
    POSTGRES_USER: str = "aihub_user"
    POSTGRES_PASSWORD: str = "aihub_password"

    @property
    def database_url(self) -> str:
        """Async DSN for SQLAlchemy (asyncpg driver)."""
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def database_url_sync(self) -> str:
        """Sync DSN for Alembic migrations (psycopg2 driver)."""
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # ------------------------------------------------------------------
    # Redis
    # ------------------------------------------------------------------
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""
    REDIS_DB: int = 0

    @property
    def redis_url(self) -> str:
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # ------------------------------------------------------------------
    # JWT
    # ------------------------------------------------------------------
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ------------------------------------------------------------------
    # OpenAI / LLM
    # ------------------------------------------------------------------
    OPENAI_API_KEY: str
    OPENAI_API_BASE: str = "https://api.openai.com/v1"  # Can be Groq or other compatible endpoint
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    OPENAI_MAX_TOKENS: int = 2048
    OPENAI_TEMPERATURE: float = 0.7

    # ------------------------------------------------------------------
    # Vector Store
    # ------------------------------------------------------------------
    VECTOR_STORE_TYPE: str = "chroma"   # "chroma" | "pgvector"
    CHROMA_PERSIST_DIR: str = "./data/chroma"

    # ------------------------------------------------------------------
    # File Uploads
    # ------------------------------------------------------------------
    UPLOAD_DIR: str = "./data/uploads"
    MAX_UPLOAD_SIZE_MB: int = 20
    ALLOWED_EXTENSIONS: str = "pdf,txt,md,docx,csv"

    @property
    def allowed_extensions_list(self) -> List[str]:
        return [e.strip().lower() for e in self.ALLOWED_EXTENSIONS.split(",")]

    # ------------------------------------------------------------------
    # Subscription Limits
    # ------------------------------------------------------------------
    FREE_PLAN_MONTHLY_TOKENS: int = 50_000
    PRO_PLAN_MONTHLY_TOKENS: int = 500_000
    ENTERPRISE_PLAN_MONTHLY_TOKENS: int = 5_000_000
    FREE_PLAN_DAILY_REQUESTS: int = 20
    PRO_PLAN_DAILY_REQUESTS: int = 500
    ENTERPRISE_PLAN_DAILY_REQUESTS: int = 10_000

    # ------------------------------------------------------------------
    # Stripe
    # ------------------------------------------------------------------
    STRIPE_SECRET_KEY: str = ""
    STRIPE_PUBLISHABLE_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_PRO_PRICE_ID: str = ""
    STRIPE_ENTERPRISE_PRICE_ID: str = ""

    # ------------------------------------------------------------------
    # Admin
    # ------------------------------------------------------------------
    ADMIN_EMAIL: str = "admin@aihub.local"
    ADMIN_PASSWORD: str = "Admin@12345"

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"    # "json" | "text"
    LOG_FILE: str = ""

    # ------------------------------------------------------------------
    # URLs
    # ------------------------------------------------------------------
    FRONTEND_URL: str = "http://localhost:8501"
    BACKEND_URL: str = "http://localhost:8000"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return the cached Settings singleton.

    Using lru_cache means the .env file is read exactly once at
    startup, not on every function call.  This is safe because
    settings don't change while the app is running.
    """
    return Settings()


# Module-level convenience alias
settings: Settings = get_settings()
