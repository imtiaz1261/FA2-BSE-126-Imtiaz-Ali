"""
preprocessing.py
------------------
Text cleaning and normalization utilities.

Keeps preprocessing intentionally light for a semantic search use case:
modern sentence embedding models are trained on natural language and
generally perform *worse* if you aggressively strip stopwords / punctuation
/ lowercase everything (that style of preprocessing is more appropriate for
classic keyword-based methods like TF-IDF or BM25).

So this module provides two levels:
    - clean_text(): safe normalization for BOTH embeddings and keyword search
      (whitespace collapsing, encoding fixes, control-character removal).
    - normalize_for_keyword_search(): heavier normalization (lowercase,
      punctuation stripped) used only for the traditional keyword-search
      comparison feature.
"""

from __future__ import annotations

import re
import string
import unicodedata


_WHITESPACE_RE = re.compile(r"\s+")
_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def clean_text(text: str) -> str:
    """
    Normalize a raw document's text for embedding generation.

    Steps:
        1. Normalize unicode (e.g., fancy quotes / accents -> canonical form)
        2. Strip control characters that sometimes leak in from PDFs
        3. Collapse repeated whitespace / newlines into single spaces
        4. Trim leading/trailing whitespace

    Note: we deliberately preserve case and punctuation, since sentence
    embedding models use that information.
    """
    if not text:
        return ""

    text = unicodedata.normalize("NFKC", text)
    text = _CONTROL_CHARS_RE.sub(" ", text)
    text = _WHITESPACE_RE.sub(" ", text)
    return text.strip()


def truncate_for_preview(text: str, max_chars: int = 220) -> str:
    """Return a short preview snippet of a document for display purposes."""
    text = text.strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rsplit(" ", 1)[0] + "..."


def normalize_for_keyword_search(text: str) -> str:
    """
    Heavier normalization used only by the traditional keyword-search
    baseline (bonus feature comparing semantic vs. keyword search):
        - lowercase
        - strip punctuation
        - collapse whitespace
    """
    text = clean_text(text).lower()
    text = text.translate(str.maketrans("", "", string.punctuation))
    text = _WHITESPACE_RE.sub(" ", text)
    return text.strip()


def preprocess_documents(documents):
    """
    Apply clean_text() to a list of Document objects in place and return them.
    Adds a `.clean_text` attribute alongside the original `.raw_text`.
    """
    for doc in documents:
        doc.metadata["clean_text"] = clean_text(doc.raw_text)
    return documents
