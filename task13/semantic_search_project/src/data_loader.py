"""
data_loader.py
---------------
Responsible for loading raw documents from a local directory.

Supports:
    - .txt files (UTF-8, with graceful fallback for other encodings)
    - .pdf files (optional, requires `pypdf`) - bonus feature

Each loaded document is returned as a dictionary with:
    {
        "doc_id": int,
        "filename": str,
        "filepath": str,
        "title": str,
        "category": str | None,   # parsed from optional metadata header
        "raw_text": str,
    }

Design notes:
    - Loading is intentionally decoupled from preprocessing (see
      preprocessing.py) so each stage can be tested / swapped independently.
    - A simple "Title:" / "Category:" header convention is supported so the
      project can demonstrate metadata filtering, but plain text files
      without any header still work fine.
"""

from __future__ import annotations

import os
import logging
from dataclasses import dataclass, field
from typing import List, Optional

logger = logging.getLogger(__name__)

SUPPORTED_TEXT_EXTENSIONS = {".txt"}
SUPPORTED_PDF_EXTENSIONS = {".pdf"}


@dataclass
class Document:
    """Simple container for a loaded document."""
    doc_id: int
    filename: str
    filepath: str
    raw_text: str
    title: Optional[str] = None
    category: Optional[str] = None
    metadata: dict = field(default_factory=dict)


def _read_text_file(filepath: str) -> str:
    """
    Read a text file robustly, handling encoding issues gracefully.
    Tries UTF-8 first, falls back to latin-1 if that fails.
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except UnicodeDecodeError:
        logger.warning("UTF-8 decode failed for %s, retrying with latin-1", filepath)
        with open(filepath, "r", encoding="latin-1") as f:
            return f.read()


def _read_pdf_file(filepath: str) -> str:
    """
    Read a PDF file and extract its text content.
    Requires the optional `pypdf` dependency (bonus feature: PDF support).
    """
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise ImportError(
            "PDF support requires 'pypdf'. Install it with: pip install pypdf"
        ) from exc

    reader = PdfReader(filepath)
    text_parts = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(text_parts)


def _parse_header_metadata(raw_text: str) -> tuple[Optional[str], Optional[str], str]:
    """
    Parse an optional "Title:" / "Category:" header from the top of a
    document. Returns (title, category, remaining_body_text).

    If no header is present, the full text is treated as the body and
    title/category are left as None.
    """
    lines = raw_text.splitlines()
    title, category = None, None
    consumed = 0

    for line in lines[:5]:  # only scan first few lines for a header
        stripped = line.strip()
        if stripped.lower().startswith("title:"):
            title = stripped.split(":", 1)[1].strip()
            consumed += 1
        elif stripped.lower().startswith("category:"):
            category = stripped.split(":", 1)[1].strip()
            consumed += 1
        elif stripped == "":
            consumed += 1
        else:
            break

    body = "\n".join(lines[consumed:]) if consumed else raw_text
    return title, category, body


def load_documents(directory: str, limit: Optional[int] = None) -> List[Document]:
    """
    Load all supported documents (.txt, .pdf) from `directory`.

    Args:
        directory: path to a folder containing documents.
        limit: optional cap on number of documents to load (useful for
               quick testing on a subset).

    Returns:
        A list of Document objects, sorted by filename for reproducibility.

    Raises:
        FileNotFoundError: if the directory does not exist.
        ValueError: if no supported documents are found.
    """
    if not os.path.isdir(directory):
        raise FileNotFoundError(f"Document directory not found: {directory}")

    filenames = sorted(os.listdir(directory))
    documents: List[Document] = []
    doc_id = 1

    for filename in filenames:
        filepath = os.path.join(directory, filename)
        if not os.path.isfile(filepath):
            continue

        ext = os.path.splitext(filename)[1].lower()
        try:
            if ext in SUPPORTED_TEXT_EXTENSIONS:
                raw_text = _read_text_file(filepath)
            elif ext in SUPPORTED_PDF_EXTENSIONS:
                raw_text = _read_pdf_file(filepath)
            else:
                continue  # skip unsupported file types silently

            if not raw_text or not raw_text.strip():
                logger.warning("Skipping empty document: %s", filename)
                continue

            title, category, body = _parse_header_metadata(raw_text)
            documents.append(
                Document(
                    doc_id=doc_id,
                    filename=filename,
                    filepath=filepath,
                    raw_text=body,
                    title=title or filename,
                    category=category,
                )
            )
            doc_id += 1

        except Exception as exc:  # noqa: BLE001 - log and continue loading others
            logger.error("Failed to load %s: %s", filename, exc)
            continue

        if limit is not None and len(documents) >= limit:
            break

    if not documents:
        raise ValueError(f"No supported documents (.txt/.pdf) found in {directory}")

    logger.info("Loaded %d documents from %s", len(documents), directory)
    return documents
