"""
splitter.py
-----------
Text Splitting.

Breaks loaded Documents into overlapping chunks so that:
  1. Each chunk is small enough to fit comfortably in an embedding
     model's context window.
  2. Overlap between chunks preserves context that would otherwise be
     lost at a chunk boundary (e.g. a sentence split across two chunks).

Uses LangChain's RecursiveCharacterTextSplitter, which tries to split
on paragraph breaks first, then sentences, then words -- only falling
back to a hard character cut as a last resort. This keeps chunks
semantically coherent.

Metadata from the parent Document (file_name, file_type, page,
paragraph, source) is automatically propagated to every chunk by
LangChain's splitter, so traceability back to the source is preserved.
"""

from typing import List

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from config import CHUNK_SIZE, CHUNK_OVERLAP
from utils import get_logger

logger = get_logger(__name__)


def split_documents(
    documents: List[Document],
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
) -> List[Document]:
    """
    Split a list of Documents into smaller overlapping chunks.

    Parameters
    ----------
    documents : List[Document]
        Documents produced by loader.py.
    chunk_size : int
        Maximum characters per chunk (default from config: 1000).
    chunk_overlap : int
        Characters shared between consecutive chunks (default: 200).

    Returns
    -------
    List[Document]
        Chunked documents, each tagged with a `chunk_id` in metadata.
    """
    if not documents:
        logger.warning("No documents provided to splitter; returning empty list.")
        return []

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
        length_function=len,
    )

    chunks = splitter.split_documents(documents)

    # Tag each chunk with a sequential id -- useful for debugging and
    # for displaying "chunk 3 of 12" style references to the user.
    for idx, chunk in enumerate(chunks):
        chunk.metadata["chunk_id"] = idx

    logger.info(
        "Split %d document section(s) into %d chunk(s) "
        "(chunk_size=%d, chunk_overlap=%d).",
        len(documents), len(chunks), chunk_size, chunk_overlap,
    )
    return chunks