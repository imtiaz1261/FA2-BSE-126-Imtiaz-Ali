"""
Local file storage for uploaded documents.

Files are stored on disk under `<backend>/<STORAGE_DIR>/<user_id>/`.
This is intentionally simple (local disk, not S3) — swapping to
object storage later only means changing this one module.
"""

import logging
import uuid
from pathlib import Path

from fastapi import UploadFile

from app.core.config import BACKEND_DIR, settings

logger = logging.getLogger(__name__)

STORAGE_ROOT = BACKEND_DIR / settings.STORAGE_DIR


class UploadValidationError(Exception):
    """Raised for any user-facing validation failure (type, size)."""


def _user_dir(user_id: uuid.UUID) -> Path:
    path = STORAGE_ROOT / str(user_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


def validate_upload(file: UploadFile, size_bytes: int) -> None:
    if file.content_type not in settings.ALLOWED_DOCUMENT_CONTENT_TYPES:
        raise UploadValidationError(
            f"Unsupported file type '{file.content_type}'. "
            "Allowed: PDF, DOCX, TXT, MD."
        )
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if size_bytes > max_bytes:
        raise UploadValidationError(
            f"File is too large ({size_bytes / (1024 * 1024):.1f} MB). "
            f"Max is {settings.MAX_UPLOAD_SIZE_MB} MB."
        )
    if size_bytes == 0:
        raise UploadValidationError("File is empty.")


def save_upload(user_id: uuid.UUID, file: UploadFile, content: bytes) -> tuple[str, int]:
    """Writes the file to disk and returns (storage_path, size_bytes)."""
    doc_id = uuid.uuid4()
    safe_name = Path(file.filename or "upload").name  # strip any path components
    destination = _user_dir(user_id) / f"{doc_id}_{safe_name}"

    with open(destination, "wb") as f:
        f.write(content)

    logger.info("Saved upload for user %s to %s", user_id, destination)
    return str(destination), len(content)


def delete_file(storage_path: str) -> None:
    path = Path(storage_path)
    try:
        if path.exists():
            path.unlink()
            logger.info("Deleted file %s", storage_path)
    except OSError:
        logger.exception("Failed to delete file %s", storage_path)
