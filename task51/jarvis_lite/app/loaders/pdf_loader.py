"""PDF loader — one LoadedDocument per non-empty page, via pypdf."""

import logging
from pathlib import Path
from typing import List

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.core.exceptions import DocumentLoadError
from app.loaders.base import BaseLoader, LoadedDocument

logger = logging.getLogger(__name__)


class PDFLoader(BaseLoader):
    def load(self, file_path: str) -> List[LoadedDocument]:
        path = Path(file_path)
        try:
            reader = PdfReader(str(path))
        except (PdfReadError, OSError) as exc:
            logger.exception("Failed to open PDF %s", file_path)
            raise DocumentLoadError(f"Could not open PDF '{path.name}': {exc}") from exc

        documents: List[LoadedDocument] = []
        for page_number, page in enumerate(reader.pages, start=1):
            try:
                text = page.extract_text() or ""
            except Exception as exc:  # pypdf can raise on malformed pages
                logger.warning("Failed to extract text from page %s of %s: %s", page_number, path.name, exc)
                continue

            if text.strip():
                documents.append(
                    LoadedDocument(
                        content=text,
                        metadata={
                            "source": str(path),
                            "filename": path.name,
                            "file_type": "pdf",
                            "page": page_number,
                        },
                    )
                )

        logger.info("Loaded %d page(s) with text from %s", len(documents), path.name)
        return documents
