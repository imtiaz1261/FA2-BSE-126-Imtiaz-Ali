"""
Centralized configuration management for the RAG Evaluation Pipeline.

Uses pydantic-settings so that:
  - All configuration is validated at startup (fail fast on bad config).
  - Environment variables and a `.env` file are the single source of truth.
  - Every other module imports `settings` from here instead of calling
    `os.getenv` directly, which prevents config drift across the codebase.
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMProvider(str, Enum):
    OPENAI = "openai"
    GROQ = "groq"
    LOCAL = "local"


class VectorStoreBackend(str, Enum):
    FAISS = "faiss"
    CHROMA = "chroma"


class Settings(BaseSettings):
    """Application-wide settings loaded from environment variables / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- LLM provider ---
    llm_provider: LLMProvider = Field(default=LLMProvider.GROQ, alias="LLM_PROVIDER")
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")
    groq_api_key: str | None = Field(default=None, alias="GROQ_API_KEY")
    groq_model: str = Field(default="llama-3.1-8b-instant", alias="GROQ_MODEL")
    groq_base_url: str = Field(
        default="https://api.groq.com/openai/v1", alias="GROQ_BASE_URL"
    )
    local_model_name: str = Field(
        default="meta-llama/Llama-3.1-8B-Instruct", alias="LOCAL_MODEL_NAME"
    )

    # --- Embeddings ---
    # Groq does not offer an embeddings endpoint, so embeddings always run
    # locally via sentence-transformers (HuggingFace) regardless of which
    # LLM provider is generating answers. This field also doubles as the
    # OpenAI embedding model name if you switch llm_provider back to openai
    # and want to use OpenAI embeddings instead (see rag_pipeline/retriever.py).
    embedding_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2", alias="EMBEDDING_MODEL"
    )

    # --- Vector store ---
    vector_store_backend: VectorStoreBackend = Field(
        default=VectorStoreBackend.FAISS, alias="VECTOR_STORE_BACKEND"
    )
    vector_store_path: Path = Field(
        default=Path("./data/vector_store"), alias="VECTOR_STORE_PATH"
    )

    # --- Evaluation dataset ---
    eval_dataset_path: Path = Field(
        default=Path("./dataset/evaluation_dataset.json"), alias="EVAL_DATASET_PATH"
    )

    # --- Reporting ---
    reports_output_dir: Path = Field(
        default=Path("./reports/output"), alias="REPORTS_OUTPUT_DIR"
    )

    # --- Logging ---
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_to_file: bool = Field(default=True, alias="LOG_TO_FILE")
    log_file_path: Path = Field(default=Path("./logs/pipeline.log"), alias="LOG_FILE_PATH")

    # --- RAGAS ---
    ragas_llm_model: str = Field(default="gpt-4o-mini", alias="RAGAS_LLM_MODEL")
    ragas_embedding_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2", alias="RAGAS_EMBEDDING_MODEL"
    )

    @model_validator(mode="after")
    def _validate_provider_requirements(self) -> "Settings":
        """Fail fast if the selected LLM provider is missing required config."""
        if self.llm_provider == LLMProvider.OPENAI and not self.openai_api_key:
            raise ValueError(
                "OPENAI_API_KEY must be set when LLM_PROVIDER=openai. "
                "Add it to your .env file (see .env.example)."
            )
        if self.llm_provider == LLMProvider.GROQ and not self.groq_api_key:
            raise ValueError(
                "GROQ_API_KEY must be set when LLM_PROVIDER=groq. "
                "Add it to your .env file (see .env.example)."
            )
        return self

    def ensure_directories(self) -> None:
        """Create all output directories the pipeline writes to, if missing."""
        self.reports_output_dir.mkdir(parents=True, exist_ok=True)
        self.vector_store_path.mkdir(parents=True, exist_ok=True)
        self.log_file_path.parent.mkdir(parents=True, exist_ok=True)


# Singleton settings instance — import this everywhere:
#   from config.settings import settings
settings = Settings()
