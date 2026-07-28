"""
rag/vector_store.py
--------------------
Builds an in-memory vector index for a single document on demand
(when the user asks about a specific file), and caches it in-process
for the rest of the session so re-asking about the same file doesn't
re-embed it.

Uses a local Sentence Transformers model (no API key) and an
in-memory Chroma collection per file.
"""

from pathlib import Path
from typing import Dict, List

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from config import EMBEDDING_MODEL, RAG_TOP_K
from rag.loader import load_file
from rag.splitter import split_documents
from utils import get_logger

logger = get_logger(__name__)

_embedding_model: Embeddings = None
_file_index_cache: Dict[str, "Chroma"] = {}  # noqa: F821 (Chroma imported lazily)


def _get_embedding_model() -> Embeddings:
    global _embedding_model
    if _embedding_model is None:
        from langchain_huggingface import HuggingFaceEmbeddings

        logger.info("Loading local embedding model: %s", EMBEDDING_MODEL)
        _embedding_model = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    return _embedding_model


def _cache_key(file_path: Path) -> str:
    stat = file_path.stat()
    return f"{file_path}:{stat.st_mtime_ns}"


def get_or_build_index(file_path: Path):
    """Return a Chroma vector store for a file, building + caching it if needed."""
    from langchain_chroma import Chroma

    file_path = Path(file_path)
    key = _cache_key(file_path)

    if key in _file_index_cache:
        logger.info("Using cached vector index for %s", file_path.name)
        return _file_index_cache[key]

    docs = load_file(file_path)
    chunks = split_documents(docs)
    embedding_model = _get_embedding_model()

    logger.info("Building in-memory vector index for %s (%d chunks)", file_path.name, len(chunks))
    store = Chroma.from_documents(documents=chunks, embedding=embedding_model)
    _file_index_cache[key] = store
    return store


def get_relevant_chunks(file_path: Path, query: str, top_k: int = RAG_TOP_K) -> List[Document]:
    """Retrieve the top-k most relevant chunks from a file for a query."""
    store = get_or_build_index(file_path)
    return store.similarity_search(query, k=top_k)


def get_all_chunks(file_path: Path) -> List[Document]:
    """Return every chunk of a file (used for whole-document summarization)."""
    docs = load_file(Path(file_path))
    return split_documents(docs)
