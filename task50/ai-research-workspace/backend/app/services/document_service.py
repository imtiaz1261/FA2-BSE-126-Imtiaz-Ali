"""Document business logic — every lookup is scoped to the owning user."""

import logging
import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.document import Document, DocumentStatus
from app.services import storage_service

logger = logging.getLogger(__name__)


def list_documents(db: Session, user_id: uuid.UUID) -> list[Document]:
    stmt = (
        select(Document)
        .where(Document.user_id == user_id)
        .order_by(Document.created_at.desc())
    )
    return list(db.scalars(stmt).all())


def get_document(db: Session, user_id: uuid.UUID, document_id: uuid.UUID) -> Optional[Document]:
    stmt = select(Document).where(Document.id == document_id, Document.user_id == user_id)
    return db.scalars(stmt).first()


def create_document(
    db: Session,
    user_id: uuid.UUID,
    filename: str,
    content_type: str,
    storage_path: str,
    size_bytes: int,
) -> Document:
    document = Document(
        user_id=user_id,
        filename=filename,
        content_type=content_type,
        storage_path=storage_path,
        size_bytes=size_bytes,
        # Phase 9 (chunking/embeddings) will move this to PROCESSING -> READY.
        status=DocumentStatus.UPLOADED,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    logger.info("Created document %s (%s) for user %s", document.id, filename, user_id)
    return document


def delete_document(db: Session, user_id: uuid.UUID, document_id: uuid.UUID) -> bool:
    document = get_document(db, user_id, document_id)
    if document is None:
        return False
    storage_service.delete_file(document.storage_path)
    db.delete(document)
    db.commit()
    logger.info("Deleted document %s for user %s", document_id, user_id)
    return True
