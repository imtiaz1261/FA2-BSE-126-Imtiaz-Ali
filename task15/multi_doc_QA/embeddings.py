"""
embeddings.py
-------------
Embedding Generation.

Wraps embedding model creation behind a single `get_embedding_model()`
function so the rest of the app doesn't care whether embeddings come
from a local Sentence Transformers model or the OpenAI API.

Default: Sentence Transformers "all-MiniLM-L6-v2"
  - Runs 100% locally, no API key required, fast, 384-dim vectors.
  - Great for a beginner/intermediate project with no cloud costs.

Optional: OpenAI Embeddings ("text-embedding-3-small" by default)
  - Requires OPENAI_API_KEY in .env
  - Higher quality on some tasks, but costs money and needs internet.
"""

from langchain_core.embeddings import Embeddings

from config import (
    EMBEDDING_PROVIDER,
    SENTENCE_TRANSFORMER_MODEL,
    OPENAI_EMBEDDING_MODEL,
    OPENAI_API_KEY,
)
from utils import get_logger

logger = get_logger(__name__)


class EmbeddingModelError(Exception):
    """Raised when the requested embedding model cannot be initialized."""


def get_embedding_model(provider: str = EMBEDDING_PROVIDER) -> Embeddings:
    """
    Instantiate and return a LangChain-compatible embedding model.

    Parameters
    ----------
    provider : str
        "sentence_transformers" (default) or "openai".

    Returns
    -------
    Embeddings
        A LangChain Embeddings object with .embed_documents() / .embed_query().

    Raises
    ------
    EmbeddingModelError
        If the provider is unknown or required dependencies/keys are missing.
    """
    provider = (provider or "").lower()

    if provider == "sentence_transformers":
        try:
            from langchain_huggingface import HuggingFaceEmbeddings
        except ImportError as exc:
            raise EmbeddingModelError(
                "langchain-huggingface / sentence-transformers is not installed. "
                "Run: pip install langchain-huggingface sentence-transformers"
            ) from exc

        logger.info(
            "Loading local Sentence Transformers embedding model: %s",
            SENTENCE_TRANSFORMER_MODEL,
        )
        try:
            return HuggingFaceEmbeddings(model_name=SENTENCE_TRANSFORMER_MODEL)
        except Exception as exc:
            raise EmbeddingModelError(
                f"Failed to load Sentence Transformers model "
                f"'{SENTENCE_TRANSFORMER_MODEL}': {exc}"
            ) from exc

    elif provider == "openai":
        if not OPENAI_API_KEY:
            raise EmbeddingModelError(
                "EMBEDDING_PROVIDER is set to 'openai' but OPENAI_API_KEY is "
                "missing from your .env file."
            )
        try:
            from langchain_openai import OpenAIEmbeddings
        except ImportError as exc:
            raise EmbeddingModelError(
                "langchain-openai is not installed. Run: pip install langchain-openai"
            ) from exc

        logger.info("Loading OpenAI embedding model: %s", OPENAI_EMBEDDING_MODEL)
        return OpenAIEmbeddings(model=OPENAI_EMBEDDING_MODEL, api_key=OPENAI_API_KEY)

    else:
        raise EmbeddingModelError(
            f"Unknown EMBEDDING_PROVIDER '{provider}'. "
            "Use 'sentence_transformers' or 'openai'."
        )