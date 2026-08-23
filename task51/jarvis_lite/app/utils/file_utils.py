"""Small filesystem helpers shared by the CLI and (later) the upload route."""

import logging
from pathlib import Path

from app.config.settings import settings

logger = logging.getLogger(__name__)


def ensure_upload_dir() -> Path:
    settings.upload_dir_path.mkdir(parents=True, exist_ok=True)
    return settings.upload_dir_path


def save_upload_bytes(filename: str, content: bytes) -> str:
    """Writes raw bytes to the uploads dir and returns the saved path as a string."""
    directory = ensure_upload_dir()
    safe_name = Path(filename).name  # strip any path components from a hostile filename
    destination = directory / safe_name
    destination.write_bytes(content)
    logger.info("Saved upload to %s", destination)
    return str(destination)


def get_file_extension(file_path: str) -> str:
    return Path(file_path).suffix.lower()
