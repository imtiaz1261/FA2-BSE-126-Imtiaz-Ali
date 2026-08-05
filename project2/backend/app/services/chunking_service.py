"""
Text chunking service — Phase 9.

Converts paged raw text into clean, overlapping chunks ready for
embedding.  Each chunk carries metadata (document_id, user_id,
page_number, char offsets, chunk_index) that is stored with the
vector so retrieval can surface precise citations.

Algorithm
---------
1. Clean each page's text (normalise whitespace, strip control chars).
2. Split on sentence boundaries ('. ', '! ', '? ', '\\n') to avoid
   cutting mid-sentence where possible.
3. Accumulate sentences into a chunk until CHUNK_SIZE chars is reached,
   then slide forward by (CHUNK_SIZE - CHUNK_OVERLAP) chars.
4. Return a flat list of ChunkRecord dataclasses.
"""

import re
import uuid
from dataclasses import dataclass
from typing import List, Tuple

from app.core.config import settings

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class ChunkRecord:
    document_id: uuid.UUID
    user_id: uuid.UUID
    content: str
    chunk_index: int
    page_number: int
    char_start: int
    char_end: int


# ---------------------------------------------------------------------------
# Text cleaning
# ---------------------------------------------------------------------------

# Collapse runs of whitespace/newlines into a single space, strip zero-width
# and other non-printable control characters.
_CTRL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_WHITESPACE_RE = re.compile(r"\s+")


def _clean(text: str) -> str:
    text = _CTRL_RE.sub("", text)
    text = _WHITESPACE_RE.sub(" ", text)
    return text.strip()


# ---------------------------------------------------------------------------
# Sentence-aware splitting
# ---------------------------------------------------------------------------

# Boundaries: end-of-sentence punctuation followed by whitespace, OR a blank
# line / multiple newlines (already collapsed to ' ' by _clean, but we split
# on the original boundaries first).
_SENTENCE_ENDS = re.compile(r"(?<=[.!?])\s+")


def _split_sentences(text: str) -> List[str]:
    """Split text into rough sentences while keeping the delimiter."""
    parts = _SENTENCE_ENDS.split(text)
    return [p for p in parts if p.strip()]


# ---------------------------------------------------------------------------
# Core chunking
# ---------------------------------------------------------------------------


def _chunk_text(
    text: str,
    page_number: int,
    char_offset: int,
    document_id: uuid.UUID,
    user_id: uuid.UUID,
    start_index: int,
) -> List[ChunkRecord]:
    """
    Chunk a single page's cleaned text.

    `char_offset` is the cumulative character position of this page's
    text within the full document — used to compute absolute char_start
    / char_end so multiple pages stitch together correctly.
    """
    chunk_size = settings.CHUNK_SIZE
    chunk_overlap = settings.CHUNK_OVERLAP

    sentences = _split_sentences(text)
    if not sentences:
        return []

    chunks: List[ChunkRecord] = []
    buf: List[str] = []
    buf_len = 0
    buf_start_char = char_offset
    chunk_idx = start_index

    for sentence in sentences:
        s_len = len(sentence) + 1  # +1 for the space separator

        # If adding this sentence would exceed the chunk size AND we
        # already have content, flush first.
        if buf_len + s_len > chunk_size and buf:
            content = " ".join(buf)
            chunks.append(
                ChunkRecord(
                    document_id=document_id,
                    user_id=user_id,
                    content=content,
                    chunk_index=chunk_idx,
                    page_number=page_number,
                    char_start=buf_start_char,
                    char_end=buf_start_char + len(content),
                )
            )
            chunk_idx += 1

            # Slide window: keep the last `chunk_overlap` chars worth of
            # sentences as context for the next chunk.
            overlap_buf: List[str] = []
            overlap_len = 0
            for s in reversed(buf):
                if overlap_len + len(s) + 1 <= chunk_overlap:
                    overlap_buf.insert(0, s)
                    overlap_len += len(s) + 1
                else:
                    break

            buf = overlap_buf
            buf_len = overlap_len
            buf_start_char = char_offset + len(content) - overlap_len

        buf.append(sentence)
        buf_len += s_len

    # Flush remaining text
    if buf:
        content = " ".join(buf)
        chunks.append(
            ChunkRecord(
                document_id=document_id,
                user_id=user_id,
                content=content,
                chunk_index=chunk_idx,
                page_number=page_number,
                char_start=buf_start_char,
                char_end=buf_start_char + len(content),
            )
        )

    return chunks


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

PagedText = List[Tuple[int, str]]


def chunk_document(
    pages: PagedText,
    document_id: uuid.UUID,
    user_id: uuid.UUID,
) -> List[ChunkRecord]:
    """
    Convert the paged text output of `document_loader.load_document`
    into a flat list of `ChunkRecord` objects ready for embedding and
    storage.
    """
    all_chunks: List[ChunkRecord] = []
    cumulative_offset = 0
    chunk_idx = 0

    for page_number, raw_text in pages:
        clean = _clean(raw_text)
        if not clean:
            cumulative_offset += len(raw_text)
            continue

        page_chunks = _chunk_text(
            text=clean,
            page_number=page_number,
            char_offset=cumulative_offset,
            document_id=document_id,
            user_id=user_id,
            start_index=chunk_idx,
        )
        all_chunks.extend(page_chunks)
        chunk_idx += len(page_chunks)
        cumulative_offset += len(raw_text)

    return all_chunks
