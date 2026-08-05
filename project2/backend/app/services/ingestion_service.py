"""
Document ingestion pipeline — Phase 9.

Orchestrates the full load → clean → chunk → embed → store pipeline.

Flow
----
1. Set document status to PROCESSING.
2. Load raw text from disk (PDF/DOCX/TXT/MD via document_loader).
3. Split into overlapping ChunkRecords (chunking_service).
4. Batch-embed all chunk texts (embedding_service).
5. Persist DocumentChunk rows to PostgreSQL (pgvector column populated).
6. Set document status to READY.
7. On any failure set status to FAILED and log the error.

This function is designed to run as a FastAPI BackgroundTask so the
upload endpoint returns immediately and chunking/embedding happen
asynchronously.
"""

import logging
import uuid

from sqlalchemy.orm import Session

from app.models.chunk import DocumentChunk
from app.models.document import Document, DocumentStatus
from app.services import embedding_service
from app.services.chunking_service import chunk_document
from app.services.document_loader import DocumentLoadError, load_document

logger = logging.getLogger(__name__)


async def ingest_document(document_id: uuid.UUID, db: Session) -> None:
    """
    Full ingestion pipeline for a single document.
    Called as a background task after upload.
    """
    # Re-fetch inside background task (different DB session lifecycle)
    document: Document | None = db.get(Document, document_id)
    if document is None:
        logger.error("ingest_document: document %s not found", document_id)
        return

    logger.info("Starting ingestion for document %s (%s)", document_id, document.filename)
    document.status = DocumentStatus.PROCESSING
    db.commit()

    try:
        # ── 1. Load text from disk ──────────────────────────────────────
        pages = load_document(document.storage_path)

        # ── 2. Chunk ────────────────────────────────────────────────────
        chunks = chunk_document(pages, document.id, document.user_id)
        if not chunks:
            logger.warning("Document %s produced 0 chunks — marking READY anyway", document_id)
            document.status = DocumentStatus.READY
            db.commit()
            return

        logger.info("Document %s: %d chunks generated", document_id, len(chunks))

        # ── 3. Embed ────────────────────────────────────────────────────
        texts = [c.content for c in chunks]
        embeddings = await embedding_service.embed_texts(texts)

        # ── 4. Persist chunks ───────────────────────────────────────────
        db_chunks = []
        for chunk, embedding in zip(chunks, embeddings):
            db_chunks.append(
                DocumentChunk(
                    id=uuid.uuid4(),
                    document_id=chunk.document_id,
                    user_id=chunk.user_id,
                    content=chunk.content,
                    chunk_index=chunk.chunk_index,
                    page_number=chunk.page_number,
                    char_start=chunk.char_start,
                    char_end=chunk.char_end,
                    embedding=embedding,
                )
            )

        db.add_all(db_chunks)

        # ── 5. Mark READY ───────────────────────────────────────────────
        document.status = DocumentStatus.READY
        db.commit()
        logger.info(
            "Ingestion complete for document %s — %d chunks stored",
            document_id,
            len(db_chunks),
        )

    except DocumentLoadError as exc:
        logger.error("Document %s load failed: %s", document_id, exc)
        _mark_failed(db, document)
    except embedding_service.EmbeddingServiceError as exc:
        logger.error("Document %s embedding failed: %s", document_id, exc)
        _mark_failed(db, document)
    except Exception as exc:
        logger.exception("Document %s ingestion unexpected error: %s", document_id, exc)
        _mark_failed(db, document)


def _mark_failed(db: Session, document: Document) -> None:
    try:
        document.status = DocumentStatus.FAILED
        db.commit()
    except Exception:
        logger.exception("Could not mark document %s as FAILED", document.id)
