"""
Background ingestion service for RAG document processing.

Handles async document processing: extraction, chunking, embedding generation,
and storage in pgvector. Tracks job status for frontend polling.
"""

import io
import logging
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    DocumentChunk,
    DocumentEmbedding,
    UploadedDocument,
    UploadJob,
)
from app.services.document_processor import DocumentProcessor
from app.services.embeddings import get_embedding_service

logger = logging.getLogger(__name__)


class IngestionError(Exception):
    """Raised when ingestion fails."""

    pass


async def process_document_background(
    session: AsyncSession,
    job_id: uuid.UUID,
    document_id: uuid.UUID,
    file_content: bytes,
    filename: str,
    file_type: str,
) -> None:
    """
    Process a document in the background.

    Updates upload job status and creates document chunks + embeddings.

    Args:
        session: Database session
        job_id: Upload job ID
        document_id: Document ID
        file_content: Raw file bytes
        filename: Original filename
        file_type: File extension (pdf, docx, txt, csv)

    Raises:
        IngestionError: If processing fails
    """
    try:
        logger.info(
            f"Starting ingestion: job_id={job_id}, document_id={document_id}, "
            f"filename={filename}"
        )

        # Update job status to processing
        await _update_job_status(
            session, job_id, "processing", progress=0, error_message=None
        )

        # Extract and chunk text
        chunks, metadata, error_msg = DocumentProcessor.process(
            file_content, filename, file_type
        )

        if error_msg:
            raise IngestionError(error_msg)

        if not chunks:
            raise IngestionError("No text could be extracted from document")

        logger.info(f"Extracted {len(chunks)} chunks from {filename}")

        # Update job progress
        await _update_job_status(session, job_id, "processing", progress=25)

        # Get embedding service
        embedding_service = get_embedding_service()
        embedding_model = embedding_service.model

        # Create document chunks
        chunk_objects = []
        chunk_texts = []

        for chunk_index, (chunk_text, token_count) in enumerate(chunks):
            chunk_obj = DocumentChunk(
                id=uuid.uuid4(),
                document_id=document_id,
                chunk_index=chunk_index,
                text=chunk_text,
                token_count=token_count,
                metadata=metadata,  # Could be per-chunk metadata later
            )
            chunk_objects.append(chunk_obj)
            chunk_texts.append(chunk_text)

        # Batch add chunks to session
        session.add_all(chunk_objects)
        await session.flush()  # Get IDs without committing

        logger.info(f"Created {len(chunk_objects)} chunk records")

        # Update job progress
        await _update_job_status(session, job_id, "processing", progress=50)

        # Generate embeddings in batches
        logger.info(f"Generating embeddings for {len(chunk_texts)} chunks...")

        try:
            embeddings = embedding_service.embed_batch(chunk_texts, batch_size=100)
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            raise IngestionError(f"Failed to generate embeddings: {str(e)}")

        if len(embeddings) != len(chunk_objects):
            raise IngestionError(
                f"Embedding count mismatch: expected {len(chunk_objects)}, "
                f"got {len(embeddings)}"
            )

        logger.info(f"Generated {len(embeddings)} embeddings")

        # Update job progress
        await _update_job_status(session, job_id, "processing", progress=75)

        # Create embedding records
        embedding_objects = []

        for chunk_obj, embedding in zip(chunk_objects, embeddings):
            embedding_obj = DocumentEmbedding(
                id=uuid.uuid4(),
                chunk_id=chunk_obj.id,
                document_id=document_id,
                embedding=embedding,
                embedding_model=embedding_model,
            )
            embedding_objects.append(embedding_obj)

        session.add_all(embedding_objects)

        logger.info(f"Created {len(embedding_objects)} embedding records")

        # Update document status and chunk count
        await session.execute(
            update(UploadedDocument)
            .where(UploadedDocument.id == document_id)
            .values(
                status="ready",
                chunk_count=len(chunk_objects),
                updated_at=datetime.utcnow(),
            )
        )

        # Update job status to completed
        await _update_job_status(session, job_id, "completed", progress=100)

        # Commit all changes
        await session.commit()

        logger.info(
            f"Ingestion complete: job_id={job_id}, "
            f"chunks={len(chunk_objects)}, embeddings={len(embedding_objects)}"
        )

    except IngestionError as e:
        # Known error - set error status
        logger.error(f"Ingestion error: {e}")
        await _mark_failed(session, job_id, document_id, str(e))

    except Exception as e:
        # Unexpected error
        logger.exception(f"Unexpected ingestion error: {e}")
        await _mark_failed(session, job_id, document_id, f"Unexpected error: {str(e)}")


async def _update_job_status(
    session: AsyncSession,
    job_id: uuid.UUID,
    status: str,
    progress: int = 0,
    error_message: Optional[str] = None,
) -> None:
    """Update upload job status."""
    await session.execute(
        update(UploadJob)
        .where(UploadJob.id == job_id)
        .values(
            status=status,
            progress=progress,
            error_message=error_message,
            updated_at=datetime.utcnow(),
        )
    )
    await session.commit()


async def _mark_failed(
    session: AsyncSession,
    job_id: uuid.UUID,
    document_id: uuid.UUID,
    error_message: str,
) -> None:
    """Mark job and document as failed."""
    try:
        await session.execute(
            update(UploadJob)
            .where(UploadJob.id == job_id)
            .values(
                status="failed",
                progress=0,
                error_message=error_message,
                updated_at=datetime.utcnow(),
            )
        )

        await session.execute(
            update(UploadedDocument)
            .where(UploadedDocument.id == document_id)
            .values(
                status="failed",
                error_message=error_message,
                updated_at=datetime.utcnow(),
            )
        )

        await session.commit()
    except Exception as e:
        logger.error(f"Failed to mark job as failed: {e}")


async def get_job_status(
    session: AsyncSession, job_id: uuid.UUID
) -> Optional[dict]:
    """
    Get current status of an upload job.

    Args:
        session: Database session
        job_id: Upload job ID

    Returns:
        Job status dict or None if not found
    """
    result = await session.execute(
        select(UploadJob)
        .where(UploadJob.id == job_id)
    )
    job = result.scalar_one_or_none()

    if not job:
        return None

    # Get document info if available
    document = None
    if job.document_id:
        doc_result = await session.execute(
            select(UploadedDocument)
            .where(UploadedDocument.id == job.document_id)
        )
        document = doc_result.scalar_one_or_none()

    return {
        "job_id": str(job.id),
        "document_id": str(job.document_id) if job.document_id else None,
        "status": job.status,
        "progress": job.progress,
        "chunk_count": document.chunk_count if document else 0,
        "error_message": job.error_message,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "updated_at": job.updated_at.isoformat() if job.updated_at else None,
    }


async def cleanup_old_uploads(
    session: AsyncSession, days_old: int = 30
) -> int:
    """
    Clean up old failed or orphaned upload jobs and documents.

    Args:
        session: Database session
        days_old: Delete jobs older than this many days

    Returns:
        Number of jobs deleted
    """
    from datetime import timedelta

    cutoff_date = datetime.utcnow() - timedelta(days=days_old)

    # Find old failed jobs
    result = await session.execute(
        select(UploadJob)
        .where(UploadJob.status == "failed")
        .where(UploadJob.created_at < cutoff_date)
    )
    old_jobs = result.scalars().all()

    deleted_count = 0

    for job in old_jobs:
        try:
            # Delete associated document (cascade will clean up chunks/embeddings)
            if job.document_id:
                await session.execute(
                    select(UploadedDocument)
                    .where(UploadedDocument.id == job.document_id)
                )
                # Manually delete to ensure cascade
                await session.delete(
                    await session.get(UploadedDocument, job.document_id)
                )

            # Delete job
            await session.delete(job)
            deleted_count += 1

        except Exception as e:
            logger.error(f"Error cleaning up job {job.id}: {e}")
            continue

    if deleted_count > 0:
        await session.commit()
        logger.info(f"Cleaned up {deleted_count} old upload jobs")

    return deleted_count
