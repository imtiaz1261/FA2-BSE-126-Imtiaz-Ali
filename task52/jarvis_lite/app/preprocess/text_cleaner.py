"""Text cleaning applied to every LoadedDocument before chunking.

Kept deliberately conservative — this normalizes whitespace and strips
non-printable junk without rewriting the author's actual words, since
aggressive cleaning can silently damage retrieval quality.
"""

import logging
import re
import unicodedata
from typing import List

from app.core.exceptions import EmptyDocumentError
from app.loaders.base import LoadedDocument

logger = logging.getLogger(__name__)

# Control characters (except \n and \t) that sometimes leak in from PDF extraction.
_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_MULTI_SPACE_RE = re.compile(r"[ \t]+")
_MULTI_BLANK_LINE_RE = re.compile(r"\n{3,}")


def clean_text(text: str) -> str:
    """Normalizes line endings/whitespace and strips control characters."""
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _CONTROL_CHARS_RE.sub("", text)
    text = _MULTI_SPACE_RE.sub(" ", text)
    text = _MULTI_BLANK_LINE_RE.sub("\n\n", text)
    return text.strip()


def clean_documents(documents: List[LoadedDocument]) -> List[LoadedDocument]:
    """Cleans each document's content, dropping any that end up empty.

    Raises `EmptyDocumentError` if cleaning wipes out every document
    (e.g. a "text" PDF that was actually just scanned images).
    """
    cleaned: List[LoadedDocument] = []
    for doc in documents:
        text = clean_text(doc.content)
        if text:
            cleaned.append(LoadedDocument(content=text, metadata=doc.metadata))
        else:
            logger.warning("Dropped empty document unit after cleaning: %s", doc.metadata)

    if not cleaned:
        raise EmptyDocumentError("All content was removed during cleaning — nothing left to chunk.")

    return cleaned
