"""
Document loader service — Phase 9.

Extracts plain text from uploaded files.  Each loader returns a list
of (page_number, text) tuples so the chunker can preserve page-level
metadata.  Page number is 1-based; for formats without pages (TXT, MD)
every tuple gets page_number=1.

Supported formats
-----------------
  PDF   — via pypdf (pure-Python, no external dependencies)
  DOCX  — via python-docx
  TXT   — decoded as UTF-8 with latin-1 fallback
  MD    — same as TXT
"""

import logging
from pathlib import Path
from typing import List, Tuple

logger = logging.getLogger(__name__)

# Type alias:  list of (page_number, page_text) tuples
PagedText = List[Tuple[int, str]]


class DocumentLoadError(Exception):
    """Raised when a file cannot be parsed."""


# ---------------------------------------------------------------------------
# Individual loaders
# ---------------------------------------------------------------------------


def _load_pdf(path: Path) -> PagedText:
    try:
        from pypdf import PdfReader  # lazy import — optional dep
    except ImportError as exc:
        raise DocumentLoadError(
            "pypdf is not installed. Add pypdf to requirements.txt."
        ) from exc

    try:
        reader = PdfReader(str(path))
    except Exception as exc:
        raise DocumentLoadError(f"Could not open PDF: {exc}") from exc

    pages: PagedText = []
    for page_num, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception:
            logger.warning("Failed to extract text from PDF page %d", page_num)
            text = ""
        pages.append((page_num, text))

    return pages


def _load_docx(path: Path) -> PagedText:
    try:
        from docx import Document  # lazy import — optional dep
    except ImportError as exc:
        raise DocumentLoadError(
            "python-docx is not installed. Add python-docx to requirements.txt."
        ) from exc

    try:
        doc = Document(str(path))
    except Exception as exc:
        raise DocumentLoadError(f"Could not open DOCX: {exc}") from exc

    # DOCX has no native page concept — treat each paragraph as part of page 1
    # and insert a rough page break every ~50 paragraphs so metadata is useful.
    pages: PagedText = []
    current_page = 1
    para_texts: List[str] = []

    for i, para in enumerate(doc.paragraphs, start=1):
        text = para.text.strip()
        if text:
            para_texts.append(text)
        if i % 50 == 0:
            pages.append((current_page, "\n".join(para_texts)))
            current_page += 1
            para_texts = []

    if para_texts:
        pages.append((current_page, "\n".join(para_texts)))

    return pages if pages else [(1, "")]


def _load_text(path: Path) -> PagedText:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = path.read_text(encoding="latin-1")
    except Exception as exc:
        raise DocumentLoadError(f"Could not read text file: {exc}") from exc

    return [(1, text)]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

_LOADER_MAP = {
    ".pdf": _load_pdf,
    ".docx": _load_docx,
    ".txt": _load_text,
    ".md": _load_text,
}


def load_document(storage_path: str) -> PagedText:
    """
    Load a document from disk and return a list of (page_number, text)
    tuples.  Raises DocumentLoadError if the file cannot be parsed.
    """
    path = Path(storage_path)
    if not path.exists():
        raise DocumentLoadError(f"File not found: {storage_path}")

    suffix = path.suffix.lower()
    loader = _LOADER_MAP.get(suffix)
    if loader is None:
        raise DocumentLoadError(
            f"Unsupported file extension '{suffix}'. "
            "Supported: .pdf, .docx, .txt, .md"
        )

    logger.info("Loading document: %s", path.name)
    pages = loader(path)
    total_chars = sum(len(t) for _, t in pages)
    logger.info(
        "Loaded %d page(s), %d chars from %s", len(pages), total_chars, path.name
    )
    return pages
