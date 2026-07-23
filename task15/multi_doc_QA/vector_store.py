"""
vector_store.py
----------------
Vector Database management.

Handles building a new vector store from chunked documents, persisting
it to disk, and loading an existing one back up -- so the (potentially
slow/expensive) embedding step only has to run once per document set.

Default backend: ChromaDB (embedded, no server required, persists to
a local folder).
Optional backend: FAISS (in-memory index, persisted via save/load to
a local folder).
"""

from pathlib import Path
from typing import List, Optional

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.vectorstores import VectorStore

from config import (
    VECTOR_STORE_PROVIDER,
    VECTOR_DB_DIR,
    CHROMA_COLLECTION_NAME,
    FAISS_INDEX_DIR,
)
from utils import get_logger

logger = get_logger(__name__)


class VectorStoreError(Exception):
    """Raised when the vector store cannot be built or loaded."""


def _chroma_exists(persist_dir: Path) -> bool:
    return persist_dir.exists() and any(persist_dir.iterdir())


def _faiss_exists(persist_dir: Path) -> bool:
    return persist_dir.exists() and (persist_dir / "index.faiss").exists()


def build_vector_store(
    chunks: List[Document],
    embedding_model: Embeddings,
    provider: str = VECTOR_STORE_PROVIDER,
    persist_dir: Optional[Path] = None,
) -> VectorStore:
    """
    Build a new vector store from document chunks and persist it to disk.

    Parameters
    ----------
    chunks : List[Document]
        Chunked documents from splitter.py.
    embedding_model : Embeddings
        Embedding model from embeddings.py.
    provider : str
        "chroma" (default) or "faiss".
    persist_dir : Path, optional
        Override the default persistence directory.

    Returns
    -------
    VectorStore
    """
    if not chunks:
        raise VectorStoreError("Cannot build a vector store from zero chunks.")

    provider = (provider or "").lower()

    if provider == "chroma":
        from langchain_chroma import Chroma

        target_dir = persist_dir or VECTOR_DB_DIR
        target_dir.mkdir(parents=True, exist_ok=True)

        logger.info(
            "Building Chroma vector store (%d chunks) at '%s' ...",
            len(chunks), target_dir,
        )
        store = Chroma.from_documents(
            documents=chunks,
            embedding=embedding_model,
            collection_name=CHROMA_COLLECTION_NAME,
            persist_directory=str(target_dir),
        )
        logger.info("Chroma vector store built and persisted successfully.")
        return store

    elif provider == "faiss":
        from langchain_community.vectorstores import FAISS

        target_dir = persist_dir or FAISS_INDEX_DIR
        target_dir.mkdir(parents=True, exist_ok=True)

        logger.info("Building FAISS index (%d chunks) ...", len(chunks))
        store = FAISS.from_documents(chunks, embedding_model)
        store.save_local(str(target_dir))
        logger.info("FAISS index built and saved to '%s'.", target_dir)
        return store

    else:
        raise VectorStoreError(
            f"Unknown VECTOR_STORE_PROVIDER '{provider}'. Use 'chroma' or 'faiss'."
        )


def load_vector_store(
    embedding_model: Embeddings,
    provider: str = VECTOR_STORE_PROVIDER,
    persist_dir: Optional[Path] = None,
) -> Optional[VectorStore]:
    """
    Load a previously persisted vector store from disk, if one exists.

    Returns
    -------
    VectorStore or None
        None if no persisted store is found (caller should then build one).
    """
    provider = (provider or "").lower()

    if provider == "chroma":
        from langchain_chroma import Chroma

        target_dir = persist_dir or VECTOR_DB_DIR
        if not _chroma_exists(target_dir):
            logger.info("No existing Chroma store found at '%s'.", target_dir)
            return None

        logger.info("Loading existing Chroma vector store from '%s' ...", target_dir)
        return Chroma(
            collection_name=CHROMA_COLLECTION_NAME,
            embedding_function=embedding_model,
            persist_directory=str(target_dir),
        )

    elif provider == "faiss":
        from langchain_community.vectorstores import FAISS

        target_dir = persist_dir or FAISS_INDEX_DIR
        if not _faiss_exists(target_dir):
            logger.info("No existing FAISS index found at '%s'.", target_dir)
            return None

        logger.info("Loading existing FAISS index from '%s' ...", target_dir)
        return FAISS.load_local(
            str(target_dir), embedding_model, allow_dangerous_deserialization=True
        )

    else:
        raise VectorStoreError(
            f"Unknown VECTOR_STORE_PROVIDER '{provider}'. Use 'chroma' or 'faiss'."
        )


def get_or_build_vector_store(
    chunks_provider,
    embedding_model: Embeddings,
    provider: str = VECTOR_STORE_PROVIDER,
    force_rebuild: bool = False,
) -> VectorStore:
    """
    Convenience wrapper: load an existing store if available, otherwise
    build a new one.

    Parameters
    ----------
    chunks_provider : Callable[[], List[Document]]
        A zero-argument function that returns chunks -- only called if
        a new store actually needs to be built (avoids re-loading and
        re-splitting documents unnecessarily).
    force_rebuild : bool
        If True, ignore any existing persisted store and rebuild.
    """
    if not force_rebuild:
        existing = load_vector_store(embedding_model, provider)
        if existing is not None:
            return existing

    chunks = chunks_provider()
    return build_vector_store(chunks, embedding_model, provider)