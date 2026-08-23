"""
FastAPI routes for RAG document management.

Endpoints:
- POST /documents/upload - Upload a document for indexing
- GET /documents/status/{job_id} - Poll upload job status
- GET /documents - List documents in a conversation
- DELETE /documents/{document_id} - Delete a document and its chunks
- POST /documents/{document_id}/retrieve - Retrieve relevant chunks for a query
"""

import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models import Message, UploadedDocument, UploadJob, User
from app.schemas_rag import (
    CitationMetadata,
    DocumentDeleteRequest,
    DocumentListResponse,
    DocumentMetadata,
    DocumentUploadRequest,
    RetrievalResult,
    RetrievedChunk,
    UploadJobResponse,
    UploadStatusResponse,
)
from app.services.document_processor import validate_file_type
from app.services.ingestion import get_job_status, process_document_background
from app.services.retrieval import hybrid_search

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])


# ============================================================================
# Upload Endpoint
# ============================================================================


@router.post("/upload", response_model=UploadJobResponse)
async def upload_document(
    file: UploadFile = File(...),
    conversation_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload a document for RAG indexing.

    Accepts PDF, DOCX, TXT, CSV up to 20MB. Returns a job ID for polling status.

    Args:
        file: File to upload
        conversation_id: Optional conversation to scope document to
        db: Database session
        current_user: Authenticated user

    Returns:
        Upload job with ID for polling
    """
    try:
        # Validate file type
        file_extension = file.filename.split(".")[-1].lower()

        if not validate_file_type(file_extension):
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {file_extension}. "
                f"Supported: pdf, docx, txt, csv",
            )

        # Parse conversation ID if provided
        conversation_uuid: Optional[uuid.UUID] = None
        if conversation_id:
            try:
                conversation_uuid = uuid.UUID(conversation_id)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid conversation ID")

        # Read file content
        file_content = await file.read()

        if not file_content:
            raise HTTPException(status_code=400, detail="File is empty")

        # Create UploadedDocument record
        document_id = uuid.uuid4()
        document = UploadedDocument(
            id=document_id,
            user_id=current_user.id,
            conversation_id=conversation_uuid,
            filename=file.filename,
            file_type=file_extension,
            file_size_bytes=len(file_content),
            status="pending",
            chunk_count=0,
        )
        db.add(document)
        await db.flush()

        # Create UploadJob record
        job_id = uuid.uuid4()
        job = UploadJob(
            id=job_id,
            user_id=current_user.id,
            document_id=document_id,
            status="pending",
            progress=0,
        )
        db.add(job)
        await db.commit()

        logger.info(
            f"Created upload job: job_id={job_id}, document_id={document_id}, "
            f"user_id={current_user.id}, filename={file.filename}"
        )

        # Start background ingestion task
        # In production, use Celery, RQ, or similar
        # For now, use asyncio.create_task() or similar
        try:
            # Queue the background task (implementation depends on your task queue)
            # For demonstration, we'll trigger it synchronously with proper error handling
            import asyncio

            asyncio.create_task(
                process_document_background(
                    db,
                    job_id,
                    document_id,
                    file_content,
                    file.filename,
                    file_extension,
                )
            )
        except Exception as e:
            logger.error(f"Failed to queue ingestion task: {e}")
            # Job created, but background task failed to start
            # Client can still poll status and see the error

        return UploadJobResponse(
            job_id=job_id,
            document_id=document_id,
            status="pending",
            progress=0,
            error_message=None,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload document")


# ============================================================================
# Status Polling Endpoint
# ============================================================================


@router.get("/status/{job_id}", response_model=UploadStatusResponse)
async def get_upload_status(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Poll the status of an upload job.

    Args:
        job_id: Job ID from upload response
        db: Database session
        current_user: Authenticated user

    Returns:
        Job status with progress and chunk count
    """
    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID format")

    try:
        # Get job from database
        result = await db.execute(
            select(UploadJob).where(
                and_(
                    UploadJob.id == job_uuid,
                    UploadJob.user_id == current_user.id,
                )
            )
        )
        job = result.scalar_one_or_none()

        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        # Get document if available
        document = None
        if job.document_id:
            doc_result = await db.execute(
                select(UploadedDocument).where(UploadedDocument.id == job.document_id)
            )
            document = doc_result.scalar_one_or_none()

        return UploadStatusResponse(
            job_id=job.id,
            document_id=job.document_id,
            status=job.status,
            progress=job.progress,
            chunk_count=document.chunk_count if document else 0,
            error_message=job.error_message,
            created_at=job.created_at,
            updated_at=job.updated_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Status check error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get job status")


# ============================================================================
# List Documents Endpoint
# ============================================================================


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    conversation_id: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List documents for a conversation or user.

    Args:
        conversation_id: Optional conversation to filter by
        status_filter: Optional status filter (pending, processing, ready, failed)
        db: Database session
        current_user: Authenticated user

    Returns:
        List of documents with metadata
    """
    try:
        # Build query
        query = select(UploadedDocument).where(
            UploadedDocument.user_id == current_user.id
        )

        # Filter by conversation if provided
        if conversation_id:
            try:
                conversation_uuid = uuid.UUID(conversation_id)
                query = query.where(UploadedDocument.conversation_id == conversation_uuid)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid conversation ID")

        # Filter by status if provided
        if status_filter:
            if status_filter not in ["pending", "processing", "ready", "failed"]:
                raise HTTPException(status_code=400, detail="Invalid status filter")
            query = query.where(UploadedDocument.status == status_filter)

        # Sort by created_at descending
        query = query.order_by(UploadedDocument.created_at.desc())

        result = await db.execute(query)
        documents = result.scalars().all()

        doc_metadata = [
            DocumentMetadata(
                id=doc.id,
                filename=doc.filename,
                file_type=doc.file_type,
                file_size_bytes=doc.file_size_bytes,
                status=doc.status,
                chunk_count=doc.chunk_count,
                error_message=doc.error_message,
                created_at=doc.created_at,
                updated_at=doc.updated_at,
            )
            for doc in documents
        ]

        return DocumentListResponse(
            documents=doc_metadata,
            total_count=len(doc_metadata),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"List documents error: {e}")
        raise HTTPException(status_code=500, detail="Failed to list documents")


# ============================================================================
# Delete Document Endpoint
# ============================================================================


@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a document and all its chunks/embeddings.

    Args:
        document_id: Document to delete
        db: Database session
        current_user: Authenticated user

    Returns:
        Success message
    """
    try:
        doc_uuid = uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document ID format")

    try:
        # Verify document belongs to user
        result = await db.execute(
            select(UploadedDocument).where(
                and_(
                    UploadedDocument.id == doc_uuid,
                    UploadedDocument.user_id == current_user.id,
                )
            )
        )
        document = result.scalar_one_or_none()

        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        # Delete document (cascade will delete chunks and embeddings)
        await db.delete(document)
        await db.commit()

        logger.info(f"Deleted document: document_id={doc_uuid}, user_id={current_user.id}")

        return {"message": "Document deleted successfully", "document_id": str(doc_uuid)}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete document error: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete document")


# ============================================================================
# Retrieve Chunks Endpoint (used internally by chat)
# ============================================================================


@router.post("/retrieve")
async def retrieve_chunks(
    query: str,
    conversation_id: Optional[str] = Query(None),
    top_k: int = Query(5, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve relevant chunks for a query using hybrid search.

    Used internally by chat endpoint to get context.

    Args:
        query: Search query
        conversation_id: Optional conversation scope
        top_k: Number of results (default 5, max 20)
        db: Database session
        current_user: Authenticated user

    Returns:
        Retrieval result with chunks and metadata
    """
    if not query or not query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    try:
        conversation_uuid: Optional[uuid.UUID] = None
        if conversation_id:
            try:
                conversation_uuid = uuid.UUID(conversation_id)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid conversation ID")

        # Run hybrid search
        chunks = await hybrid_search(
            db,
            query.strip(),
            conversation_id=conversation_uuid,
            user_id=current_user.id,
            top_k=top_k,
        )

        if not chunks:
            logger.info(
                f"No chunks found for query: {query}, "
                f"conversation_id={conversation_uuid}"
            )

        # Build response
        retrieved_chunks = [
            RetrievedChunk(
                chunk_id=uuid.UUID(chunk["chunk_id"]),
                document_id=uuid.UUID(chunk["document_id"]),
                filename=chunk["filename"],
                page_number=chunk["page_number"],
                chunk_index=chunk["chunk_index"],
                text=chunk["text"],
                relevance_score=chunk["relevance_score"],
            )
            for chunk in chunks
        ]

        return RetrievalResult(
            query=query,
            chunks=retrieved_chunks,
            total_chunks_searched=len(chunks),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Retrieval error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve chunks")
