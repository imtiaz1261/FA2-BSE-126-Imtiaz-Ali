"""Plain-text loader — reads the file as UTF-8 (with a latin-1 fallback)."""

import logging
from pathlib import Path
from typing import List

from app.core.exceptions import DocumentLoadError
from app.loaders.base import BaseLoader, LoadedDocument

logger = logging.getLogger(__name__)


class TXTLoader(BaseLoader):
    def load(self, file_path: str) -> List[LoadedDocument]:
        path = Path(file_path)
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            logger.warning("UTF-8 decode failed for %s, retrying as latin-1", path.name)
            content = path.read_text(encoding="latin-1")
        except OSError as exc:
            logger.exception("Failed to read TXT %s", file_path)
            raise DocumentLoadError(f"Could not read '{path.name}': {exc}") from exc

        if not content.strip():
            return []

        return [
            LoadedDocument(
                content=content,
                metadata={"source": str(path), "filename": path.name, "file_type": "txt"},
            )
        ]
