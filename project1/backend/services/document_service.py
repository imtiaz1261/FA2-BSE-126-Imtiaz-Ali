"""
services/document_service.py — Document Upload + RAG Processing
================================================================
Pipeline:
    Upload → save file → create DB record
    Process → load → chunk → embed → store in vector DB
    Query   → enforce limits → RAG pipeline → citations
"""

from __future__ import annotations

import hashlib
import os
import shutil
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import UploadFile
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.core.logging import get_logger
from backend.db.models.document import Document, DocumentStatus, DocumentType
from backend.db.models.usage import AIFeature, RequestStatus
from backend.services.usage_service import check_limits, log_usage
from backend.ai.rag.vector_store import get_user_collection_name, get_vector_store

logger = get_logger(__name__)

_MIME_TO_DOCTYPE = {
    "application/pdf": DocumentType.PDF,
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": DocumentType.DOCX,
    "text/plain": DocumentType.TXT,
    "text/markdown": DocumentType.MD,
    "text/csv": DocumentType.CSV,
    "application/octet-stream": DocumentType.TXT,
}

_EXT_TO_DOCTYPE = {
    ".pdf": DocumentType.PDF,
    ".docx": DocumentType.DOCX,
    ".txt": DocumentType.TXT,
    ".md": DocumentType.MD,
    ".csv": DocumentType.CSV,
}


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------

async def upload_document(
    db: AsyncSession,
    user_id: uuid.UUID,
    file: UploadFile,
) -> Document:
    """
    Save the uploaded file to disk and create a DB record with PENDING status.
    Actual processing (chunking + embedding) is triggered separately.
    """
    # Read file content
    content = await file.read()
    file_size = len(content)

    # Validate size
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if file_size > max_bytes:
        raise ValueError(f"File exceeds maximum size of {settings.MAX_UPLOAD_SIZE_MB} MB")

    # Detect type
    filename = file.filename or "upload"
    ext = Path(filename).suffix.lower()
    if ext not in _EXT_TO_DOCTYPE:
        raise ValueError(
            f"File type '{ext}' is not supported. "
            f"Allowed: {', '.join(_EXT_TO_DOCTYPE.keys())}"
        )
    doc_type = _EXT_TO_DOCTYPE[ext]

    # Compute hash for deduplication
    file_hash = hashlib.sha256(content).hexdigest()

    # Check for duplicate
    dup_result = await db.execute(
        select(Document).where(
            Document.user_id == user_id,
            Document.file_hash == file_hash,
            Document.status != DocumentStatus.FAILED,
        )
    )
    existing = dup_result.scalar_one_or_none()
    if existing:
        logger.info("document_duplicate_skipped", doc_id=str(existing.id))
        return existing

    # Save file to disk
    doc_id = uuid.uuid4()
    upload_dir = Path(settings.UPLOAD_DIR) / str(user_id) / str(doc_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / filename

    with open(file_path, "wb") as f:
        f.write(content)

    # Create DB record
    mime_type = file.content_type or "application/octet-stream"
    collection_name = get_user_collection_name(user_id)

    document = Document(
        id=doc_id,
        user_id=user_id,
        filename=filename,
        file_path=str(file_path),
        file_size_bytes=file_size,
        mime_type=mime_type,
        document_type=doc_type,
        file_hash=file_hash,
        status=DocumentStatus.PENDING,
        collection_name=collection_name,
    )
    db.add(document)
    await db.flush()

    logger.info(
        "document_uploaded",
        doc_id=str(doc_id),
        user_id=str(user_id),
        filename=filename,
        size_bytes=file_size,
    )
    return document


# ---------------------------------------------------------------------------
# Processing (chunking + embedding)
# ---------------------------------------------------------------------------

async def process_document(db: AsyncSession, document_id: uuid.UUID) -> None:
    """
    Load, chunk, embed, and store a document in the vector store.
    Updates document.status throughout the pipeline.
    """
    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()
    if not document:
        raise ValueError(f"Document {document_id} not found")

    # Mark as processing
    document.status = DocumentStatus.PROCESSING
    document.updated_at = datetime.now(timezone.utc)
    await db.flush()

    try:
        # 1. Load document
        chunks = _load_and_chunk(document)

        # 2. Embed and store
        vector_store = get_vector_store(document.collection_name)
        texts = [c.page_content for c in chunks]
        metadatas = [c.metadata for c in chunks]
        vector_store.add_texts(texts, metadatas=metadatas)

        # 3. Update record
        document.status = DocumentStatus.READY
        document.chunk_count = len(chunks)
        document.embedding_model = settings.OPENAI_EMBEDDING_MODEL
        document.processed_at = datetime.now(timezone.utc)
        document.updated_at = datetime.now(timezone.utc)

        # Get page count for PDFs
        if document.document_type == DocumentType.PDF:
            try:
                from pypdf import PdfReader
                reader = PdfReader(document.file_path)
                document.page_count = len(reader.pages)
            except Exception:
                pass

        await db.flush()
        logger.info(
            "document_processed",
            doc_id=str(document.id),
            chunks=len(chunks),
        )

    except Exception as exc:
        document.status = DocumentStatus.FAILED
        document.error_message = str(exc)[:500]
        document.updated_at = datetime.now(timezone.utc)
        await db.flush()
        logger.error(
            "document_processing_failed",
            doc_id=str(document.id),
            error=str(exc),
        )
        raise


def _load_and_chunk(document: Document):
    """Load a document and split it into chunks with metadata."""
    from langchain.text_splitter import RecursiveCharacterTextSplitter

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    file_path = document.file_path
    doc_type = document.document_type

    if doc_type == DocumentType.PDF:
        from langchain_community.document_loaders import PyPDFLoader
        loader = PyPDFLoader(file_path)
        raw_docs = loader.load()
    elif doc_type == DocumentType.DOCX:
        from langchain_community.document_loaders import Docx2txtLoader
        loader = Docx2txtLoader(file_path)
        raw_docs = loader.load()
    elif doc_type in (DocumentType.TXT, DocumentType.MD):
        from langchain_community.document_loaders import TextLoader
        loader = TextLoader(file_path, encoding="utf-8")
        raw_docs = loader.load()
    elif doc_type == DocumentType.CSV:
        from langchain_community.document_loaders import CSVLoader
        loader = CSVLoader(file_path)
        raw_docs = loader.load()
    else:
        from langchain_community.document_loaders import TextLoader
        loader = TextLoader(file_path, encoding="utf-8")
        raw_docs = loader.load()

    # Add document metadata to every chunk
    for doc in raw_docs:
        doc.metadata.update({
            "doc_id": str(document.id),
            "filename": document.filename,
            "document_type": document.document_type.value,
        })

    chunks = splitter.split_documents(raw_docs)
    return chunks


# ---------------------------------------------------------------------------
# List / Delete
# ---------------------------------------------------------------------------

async def list_documents(
    db: AsyncSession,
    user_id: uuid.UUID,
    search: Optional[str] = None,
) -> list[Document]:
    q = select(Document).where(Document.user_id == user_id)
    if search:
        q = q.where(Document.filename.ilike(f"%{search}%"))
    q = q.order_by(Document.created_at.desc())
    result = await db.execute(q)
    return list(result.scalars().all())


async def get_document(
    db: AsyncSession,
    document_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Optional[Document]:
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def delete_document(
    db: AsyncSession,
    document_id: uuid.UUID,
    user_id: uuid.UUID,
) -> bool:
    document = await get_document(db, document_id, user_id)
    if not document:
        return False

    # Delete vectors from vector store
    try:
        vector_store = get_vector_store(document.collection_name)
        # Delete by document metadata filter
        if hasattr(vector_store, "_collection"):
            vector_store._collection.delete(
                where={"doc_id": str(document_id)}
            )
    except Exception as exc:
        logger.warning("vector_delete_failed", error=str(exc))

    # Delete file from disk
    try:
        file_dir = Path(document.file_path).parent
        if file_dir.exists():
            shutil.rmtree(file_dir)
    except Exception as exc:
        logger.warning("file_delete_failed", error=str(exc))

    await db.delete(document)
    await db.flush()
    logger.info("document_deleted", doc_id=str(document_id))
    return True


# ---------------------------------------------------------------------------
# RAG Query
# ---------------------------------------------------------------------------

async def query_documents(
    db: AsyncSession,
    user_id: uuid.UUID,
    question: str,
    document_ids: Optional[list[uuid.UUID]] = None,
    top_k: int = 5,
    mode: str = "hybrid",
) -> dict:
    """
    Enforce limits → run hybrid RAG → return answer with citations.
    """
    start = time.monotonic()

    # Enforcement gate
    limit_status = await check_limits(db, user_id, AIFeature.RAG)
    if not limit_status.allowed:
        await log_usage(
            db, user_id, AIFeature.RAG, 0, 0, settings.OPENAI_MODEL,
            status=RequestStatus.BLOCKED,
            error_message=limit_status.reason,
        )
        raise ValueError(limit_status.reason)

    from backend.ai.rag.pipeline import run_rag_query
    collection_name = get_user_collection_name(user_id)
    doc_id_strings = [str(d) for d in document_ids] if document_ids else None

    result = await run_rag_query(
        question=question,
        collection_name=collection_name,
        top_k=top_k,
        mode=mode,
        document_ids=doc_id_strings,
    )

    latency = int((time.monotonic() - start) * 1000)
    await log_usage(
        db, user_id, AIFeature.RAG,
        result["prompt_tokens"], result["completion_tokens"],
        result["model"],
        latency_ms=latency,
        status=RequestStatus.SUCCESS,
    )

    return result
