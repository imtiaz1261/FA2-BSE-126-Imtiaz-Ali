"""
api/v1/routes/documents.py — Document Management + RAG Query Endpoints
=======================================================================
Routes:
    POST   /documents/upload              Upload a document
    GET    /documents/                    List documents
    GET    /documents/{id}                Get document status
    DELETE /documents/{id}                Delete a document
    POST   /documents/{id}/process        Re-process a document
    POST   /documents/query               Ask a question (RAG)
"""

import uuid
from typing import Optional

from fastapi import (
    APIRouter, BackgroundTasks, Depends, File, HTTPException,
    Query, UploadFile, status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.dependencies import get_current_active_user, get_db
from backend.core.logging import get_logger
from backend.db.models.user import User
from backend.schemas.document import (
    DocumentListResponse,
    DocumentResponse,
    DocumentStatusResponse,
    RAGQueryRequest,
    RAGQueryResponse,
    CitationSource,
)
from backend.services import document_service

router = APIRouter(prefix="/documents", tags=["Documents"])
logger = get_logger(__name__)


@router.post(
    "/upload",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a document for RAG processing",
)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> DocumentResponse:
    """
    Upload a PDF, DOCX, TXT, MD, or CSV file.

    The file is saved immediately and a background task processes it
    (chunking + embedding). Poll GET /documents/{id} to check status:
    - **pending** → queued
    - **processing** → embedding in progress
    - **ready** → queryable
    - **failed** → processing error (see error_message)
    """
    try:
        document = await document_service.upload_document(db, current_user.id, file)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    # Trigger processing in the background
    background_tasks.add_task(_process_in_background, document.id)

    return DocumentResponse.model_validate(document)


async def _process_in_background(document_id: uuid.UUID) -> None:
    """Background task: create its own DB session and process the document."""
    from backend.db.session import async_session_factory
    async with async_session_factory() as bg_db:
        try:
            await document_service.process_document(bg_db, document_id)
            await bg_db.commit()
        except Exception as exc:
            await bg_db.rollback()
            logger.error("bg_process_failed", doc_id=str(document_id), error=str(exc))


@router.get(
    "/",
    response_model=DocumentListResponse,
    summary="List uploaded documents",
)
async def list_documents(
    search: Optional[str] = Query(None, description="Search by filename"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> DocumentListResponse:
    docs = await document_service.list_documents(db, current_user.id, search=search)
    return DocumentListResponse(
        documents=[DocumentResponse.model_validate(d) for d in docs],
        total=len(docs),
    )


@router.get(
    "/{document_id}",
    response_model=DocumentStatusResponse,
    summary="Get document processing status",
)
async def get_document_status(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> DocumentStatusResponse:
    doc = await document_service.get_document(db, document_id, current_user.id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentStatusResponse(
        id=doc.id,
        filename=doc.filename,
        status=doc.status.value,
        chunk_count=doc.chunk_count,
        error_message=doc.error_message,
    )


@router.post(
    "/{document_id}/process",
    response_model=DocumentStatusResponse,
    summary="Re-process a failed or pending document",
)
async def reprocess_document(
    document_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> DocumentStatusResponse:
    doc = await document_service.get_document(db, document_id, current_user.id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    from backend.db.models.document import DocumentStatus
    doc.status = DocumentStatus.PENDING
    await db.flush()
    await db.commit()

    background_tasks.add_task(_process_in_background, document_id)
    return DocumentStatusResponse(
        id=doc.id, filename=doc.filename,
        status="pending", chunk_count=0,
    )


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a document and its embeddings",
)
async def delete_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> None:
    deleted = await document_service.delete_document(db, document_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found")


@router.post(
    "/query",
    response_model=RAGQueryResponse,
    summary="Ask a question about your uploaded documents",
)
async def query_documents(
    body: RAGQueryRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> RAGQueryResponse:
    """
    Ask a question and get an answer grounded in your uploaded documents.

    - Uses **hybrid retrieval** (vector + keyword) for best coverage
    - Returns citations with filename and page number
    - Answers are never fabricated — all claims are sourced
    """
    try:
        result = await document_service.query_documents(
            db=db,
            user_id=current_user.id,
            question=body.question,
            document_ids=body.document_ids,
            top_k=body.top_k,
            mode=body.mode,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=str(exc))

    return RAGQueryResponse(
        question=body.question,
        answer=result["answer"],
        sources=[
            CitationSource(
                document_id=s.get("document_id", ""),
                filename=s.get("filename", ""),
                page=s.get("page"),
                chunk_text=s.get("chunk_text", ""),
                score=s.get("score", 0.0),
            )
            for s in result.get("sources", [])
        ],
        tokens_used=result.get("prompt_tokens", 0) + result.get("completion_tokens", 0),
        model=result.get("model", ""),
    )


@router.get("/ping", include_in_schema=False)
async def ping():
    return {"router": "documents", "status": "ok"}
