"""Documents router — upload, list, delete. Backs the Phase 8 document manager UI."""

import logging
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.document import DocumentOut
from app.services import document_service, storage_service
from app.services.storage_service import UploadValidationError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("", response_model=list[DocumentOut])
def list_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[DocumentOut]:
    documents = document_service.list_documents(db, current_user.id)
    return [DocumentOut.model_validate(d) for d in documents]


@router.post("", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DocumentOut:
    content = await file.read()

    try:
        storage_service.validate_upload(file, len(content))
    except UploadValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    storage_path, size_bytes = storage_service.save_upload(current_user.id, file, content)

    document = document_service.create_document(
        db,
        user_id=current_user.id,
        filename=file.filename or "upload",
        content_type=file.content_type or "application/octet-stream",
        storage_path=storage_path,
        size_bytes=size_bytes,
    )
    return DocumentOut.model_validate(document)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    deleted = document_service.delete_document(db, current_user.id, document_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
