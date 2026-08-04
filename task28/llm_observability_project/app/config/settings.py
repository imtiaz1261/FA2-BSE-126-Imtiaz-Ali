import os
from functools import lru_cache
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # LLM
    llm_provider: str = os.getenv("LLM_PROVIDER", "groq")
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    model_name: str = os.getenv("MODEL_NAME", "llama-3.1-8b-instant")

    # Observability
    langfuse_public_key: str = os.getenv("LANGFUSE_PUBLIC_KEY", "")
    langfuse_secret_key: str = os.getenv("LANGFUSE_SECRET_KEY", "")
    langfuse_host: str = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
    observability_enabled: bool = bool(langfuse_public_key and langfuse_secret_key)

    # Cache
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    cache_ttl_seconds: int = int(os.getenv("CACHE_TTL_SECONDS", "3600"))

    # DB
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./data/metrics.db")

    # Security
    max_request_size_kb: int = int(os.getenv("MAX_REQUEST_SIZE_KB", "32"))
    rate_limit_per_minute: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))

    # Pricing — centralized, per 1M tokens, USD.
    # Update here whenever provider pricing changes; nothing else in the
    # codebase should hardcode a price.
    MODEL_PRICING = {
        "llama-3.1-8b-instant": {"input_per_1m": 0.05, "output_per_1m": 0.08},
        "llama-3.1-70b-versatile": {"input_per_1m": 0.59, "output_per_1m": 0.79},
        "gpt-4o-mini": {"input_per_1m": 0.15, "output_per_1m": 0.60},
    }

    # USD -> GBP conversion for display only — update this rate as needed.
    USD_TO_GBP = 0.79


@lru_cache
def get_settings() -> Settings:
    return Settings()
