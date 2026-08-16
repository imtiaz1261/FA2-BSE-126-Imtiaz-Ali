"""
config.py
---------
All tunable settings for the vector search module, sourced from
environment variables (with sane defaults) so behaviour can change
without touching code. A `.env` file is auto-loaded via python-dotenv
if present.

See .env.example for the full list of variables with descriptions.
"""
import os
from dataclasses import dataclass, field
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # python-dotenv is optional; env vars can still be set by the OS/shell.
    pass

from exceptions import ConfigurationError


def _get_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError:
        raise ConfigurationError(f"Environment variable {name}='{raw}' is not a valid integer")


def _get_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


@dataclass
class Config:
    # --- Embeddings -----------------------------------------------------
    # Provider: "sentence_transformers" (default, local/offline capable),
    #           "openai" (needs OPENAI_API_KEY),
    #           "local_tfidf" (zero-dependency offline fallback, lower quality)
    embedding_provider: str = field(default_factory=lambda: os.getenv("EMBEDDING_PROVIDER", "sentence_transformers"))
    embedding_model: str = field(default_factory=lambda: os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2"))
    openai_api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))

    # --- Vector store -----------------------------------------------------
    # Provider: "chroma" (default), "pinecone", "memory" (in-process, testing only)
    vector_db_provider: str = field(default_factory=lambda: os.getenv("VECTOR_DB_PROVIDER", "chroma"))
    collection_name: str = field(default_factory=lambda: os.getenv("COLLECTION_NAME", "jarvis_knowledge_base"))

    # Chroma
    chroma_persist_dir: str = field(default_factory=lambda: os.getenv("CHROMA_PERSIST_DIR", "./chroma_db"))

    # Pinecone
    pinecone_api_key: str = field(default_factory=lambda: os.getenv("PINECONE_API_KEY", ""))
    pinecone_index_name: str = field(default_factory=lambda: os.getenv("PINECONE_INDEX_NAME", "jarvis-knowledge-base"))
    pinecone_cloud: str = field(default_factory=lambda: os.getenv("PINECONE_CLOUD", "aws"))
    pinecone_region: str = field(default_factory=lambda: os.getenv("PINECONE_REGION", "us-east-1"))

    # --- Search behaviour ---------------------------------------------------
    top_k: int = field(default_factory=lambda: _get_int("TOP_K", 5))
    min_score: float = field(default_factory=lambda: float(os.getenv("MIN_SCORE", "0.0")))

    # --- Document processing -------------------------------------------------
    documents_dir: str = field(default_factory=lambda: os.getenv("DOCUMENTS_DIR", "./data/documents"))
    chunk_size: int = field(default_factory=lambda: _get_int("CHUNK_SIZE", 800))
    chunk_overlap: int = field(default_factory=lambda: _get_int("CHUNK_OVERLAP", 100))

    # --- Misc ---------------------------------------------------------------
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    batch_size: int = field(default_factory=lambda: _get_int("EMBEDDING_BATCH_SIZE", 32))

    def validate(self) -> None:
        """Raise ConfigurationError if the configuration is internally inconsistent."""
        if self.embedding_provider not in ("sentence_transformers", "openai", "local_tfidf"):
            raise ConfigurationError(
                f"Unknown EMBEDDING_PROVIDER '{self.embedding_provider}'. "
                "Expected one of: sentence_transformers, openai, local_tfidf"
            )
        if self.embedding_provider == "openai" and not self.openai_api_key:
            raise ConfigurationError("EMBEDDING_PROVIDER=openai requires OPENAI_API_KEY to be set")

        if self.vector_db_provider not in ("chroma", "pinecone", "memory"):
            raise ConfigurationError(
                f"Unknown VECTOR_DB_PROVIDER '{self.vector_db_provider}'. "
                "Expected one of: chroma, pinecone, memory"
            )
        if self.vector_db_provider == "pinecone" and not self.pinecone_api_key:
            raise ConfigurationError("VECTOR_DB_PROVIDER=pinecone requires PINECONE_API_KEY to be set")

        if self.top_k <= 0:
            raise ConfigurationError("TOP_K must be a positive integer")
        if self.chunk_size <= 0:
            raise ConfigurationError("CHUNK_SIZE must be a positive integer")
        if self.chunk_overlap < 0 or self.chunk_overlap >= self.chunk_size:
            raise ConfigurationError("CHUNK_OVERLAP must be >= 0 and less than CHUNK_SIZE")

    def resolved_persist_path(self) -> Path:
        p = Path(self.chroma_persist_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p


def load_config() -> Config:
    cfg = Config()
    cfg.validate()
    return cfg
