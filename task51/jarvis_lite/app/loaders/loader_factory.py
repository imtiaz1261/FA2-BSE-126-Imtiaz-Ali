"""Picks the right loader for a file based on its extension.

This is the single place that knows "which loader handles which
extension" — adding a new format later means registering it here,
nowhere else.
"""

import logging
from pathlib import Path
from typing import Dict, List, Type

from app.core.exceptions import DocumentLoadError, EmptyDocumentError, UnsupportedFileTypeError
from app.loaders.base import BaseLoader, LoadedDocument
from app.loaders.docx_loader import DOCXLoader
from app.loaders.pdf_loader import PDFLoader
from app.loaders.txt_loader import TXTLoader

logger = logging.getLogger(__name__)

_LOADER_REGISTRY: Dict[str, Type[BaseLoader]] = {
    ".pdf": PDFLoader,
    ".docx": DOCXLoader,
    ".txt": TXTLoader,
}


def get_loader(file_path: str) -> BaseLoader:
    extension = Path(file_path).suffix.lower()
    loader_cls = _LOADER_REGISTRY.get(extension)
    if loader_cls is None:
        supported = ", ".join(sorted(_LOADER_REGISTRY))
        raise UnsupportedFileTypeError(
            f"Unsupported file type '{extension}'. Supported types: {supported}."
        )
    return loader_cls()


def load_document(file_path: str) -> List[LoadedDocument]:
    """Loads a file end to end and guarantees the result isn't empty.

    Raises `UnsupportedFileTypeError`, `DocumentLoadError`, or
    `EmptyDocumentError` — callers only need to handle those three.
    """
    path = Path(file_path)
    if not path.exists():
        raise DocumentLoadError(f"File not found: {file_path}")

    loader = get_loader(file_path)
    documents = loader.load(file_path)

    if not documents:
        raise EmptyDocumentError(f"'{path.name}' contains no extractable text.")

    logger.info("Loaded %d document unit(s) from %s", len(documents), path.name)
    return documents
