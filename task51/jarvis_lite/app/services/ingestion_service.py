"""Ingestion pipeline: load -> clean -> chunk -> embed -> store.

This is the single entry point for turning a file on disk into
searchable chunks — the CLI (`main.py`) and, later, a FastAPI upload
route both call `ingest_file()` and nothing else.
"""

import logging
from pathlib import Path
from typing import Any, Dict, Optional

from app.chunking.chunker import chunk_documents
from app.config.settings import settings
from app.embeddings.base import BaseEmbeddingProvider
from app.embeddings.embedding_factory import get_embedding_provider
from app.loaders.loader_factory import load_document
from app.preprocess.text_cleaner import clean_documents
from app.vectorstore.base import BaseVectorStore
from app.vectorstore.vectorstore_factory import get_vector_store

logger = logging.getLogger(__name__)


class IngestionService:
    def __init__(
        self,
        vector_store: Optional[BaseVectorStore] = None,
        embedding_provider: Optional[BaseEmbeddingProvider] = None,
    ) -> None:
        self._vector_store = vector_store or get_vector_store()
        self._embedding_provider = embedding_provider or get_embedding_provider()

    def ingest_file(self, file_path: str) -> Dict[str, Any]:
        """Runs the full pipeline for one file and returns a small summary dict."""
        path = Path(file_path)
        logger.info("Starting ingestion for %s", path.name)

        loaded = load_document(file_path)
        cleaned = clean_documents(loaded)
        chunks = chunk_documents(
            cleaned,
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
            document_name=path.name,
        )

        embeddings = self._embedding_provider.embed_documents([c.content for c in chunks])
        self._vector_store.add_chunks(chunks, embeddings)
        self._vector_store.persist()

        logger.info("Finished ingestion for %s: %d chunk(s) stored", path.name, len(chunks))
        return {
            "filename": path.name,
            "document_units": len(loaded),
            "chunks_created": len(chunks),
        }
