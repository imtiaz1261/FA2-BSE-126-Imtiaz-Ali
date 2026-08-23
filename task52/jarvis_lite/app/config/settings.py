"""
Centralized configuration for Jarvis-Lite.

Every later phase (memory, agents, tools, voice, auth, deployment) will
read its settings from this single `Settings` object instead of calling
`os.environ` directly. All values load from a root-level `.env` file
(see `.env.example`), resolved relative to this file's location so it
works regardless of the current working directory.
"""

from functools import lru_cache
from pathlib import Path
from typing import List, Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# app/config/settings.py -> project root is 2 levels up
PROJECT_ROOT = Path(__file__).resolve().parents[2]
ROOT_ENV_FILE = PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ROOT_ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---------------------------------------------------------------
    # General
    # ---------------------------------------------------------------
    APP_NAME: str = "Jarvis-Lite"
    LOG_LEVEL: str = "INFO"

    # ---------------------------------------------------------------
    # Storage
    # ---------------------------------------------------------------
    UPLOAD_DIR: str = "data/uploads"
    SUPPORTED_FILE_TYPES: List[str] = ["pdf", "docx", "txt"]

    # ---------------------------------------------------------------
    # Chunking
    # ---------------------------------------------------------------
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 150

    # ---------------------------------------------------------------
    # Embeddings — provider is swappable via env, no code changes
    # ---------------------------------------------------------------
    EMBEDDING_PROVIDER: Literal["openai", "huggingface", "gemini"] = "huggingface"
    OPENAI_API_KEY: str = ""
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    HF_EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    GEMINI_API_KEY: str = ""
    GEMINI_EMBEDDING_MODEL: str = "models/text-embedding-004"

    # ---------------------------------------------------------------
    # LLM (final answer generation)
    # ---------------------------------------------------------------
    OPENAI_CHAT_MODEL: str = "gpt-4o-mini"
    GEMINI_CHAT_MODEL: str = "gemini-2.5-flash"
    LLM_TEMPERATURE: float = 0.2

    # ---------------------------------------------------------------
    # Vector database — Chroma is primary, FAISS is an optional backend
    # ---------------------------------------------------------------
    VECTOR_DB_PROVIDER: Literal["chroma", "faiss"] = "chroma"
    VECTOR_DB_PATH: str = "data/vector_db"
    COLLECTION_NAME: str = "jarvis_lite_docs"

    # ---------------------------------------------------------------
    # Retrieval
    # ---------------------------------------------------------------
    RETRIEVAL_TOP_K: int = Field(default=4, ge=1, le=50)

    @property
    def upload_dir_path(self) -> Path:
        return (PROJECT_ROOT / self.UPLOAD_DIR).resolve()

    @property
    def vector_db_path(self) -> Path:
        return (PROJECT_ROOT / self.VECTOR_DB_PATH).resolve()


@lru_cache
def get_settings() -> Settings:
    """Cached Settings singleton for the process."""
    return Settings()


settings = get_settings()
