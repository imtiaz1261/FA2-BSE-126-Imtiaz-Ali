"""Splits cleaned documents into overlapping chunks for embedding.

Uses LangChain's `RecursiveCharacterTextSplitter`, which tries to break
on paragraph, then sentence, then word boundaries before falling back
to a hard character cut — this keeps chunks semantically coherent far
more often than a naive fixed-width split.
"""

import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.exceptions import ChunkingError
from app.loaders.base import LoadedDocument

logger = logging.getLogger(__name__)


@dataclass
class DocumentChunk:
    """One chunk of text ready to be embedded and stored."""

    chunk_id: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)


def chunk_documents(
    documents: List[LoadedDocument],
    chunk_size: int,
    chunk_overlap: int,
    document_name: Optional[str] = None,
) -> List[DocumentChunk]:
    """Chunks every LoadedDocument and stitches together per-chunk metadata.

    Each chunk's metadata carries `document_name`, `page` (if the source
    loader provided one, e.g. PDF), `chunk_id`, `chunk_index`, and
    `source` — everything the retriever needs to cite it later.
    """
    if chunk_overlap >= chunk_size:
        raise ChunkingError(
            f"chunk_overlap ({chunk_overlap}) must be smaller than chunk_size ({chunk_size})."
        )

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    chunks: List[DocumentChunk] = []
    chunk_index = 0
    for doc in documents:
        pieces = splitter.split_text(doc.content)
        for piece in pieces:
            if not piece.strip():
                continue
            resolved_name = document_name or doc.metadata.get("filename", "unknown")
            metadata = {
                **doc.metadata,
                "document_name": resolved_name,
                "chunk_index": chunk_index,
            }
            chunk_id = f"{resolved_name}::{metadata.get('page', 0)}::{chunk_index}::{uuid.uuid4().hex[:8]}"
            chunks.append(DocumentChunk(chunk_id=chunk_id, content=piece, metadata={**metadata, "chunk_id": chunk_id}))
            chunk_index += 1

    if not chunks:
        raise ChunkingError("Chunking produced zero chunks from the given document(s).")

    logger.info("Created %d chunk(s) (size=%d, overlap=%d)", len(chunks), chunk_size, chunk_overlap)
    return chunks
