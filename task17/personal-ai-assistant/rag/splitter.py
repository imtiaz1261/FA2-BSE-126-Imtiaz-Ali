"""
rag/splitter.py
----------------
Splits loaded Documents into overlapping chunks using
RecursiveCharacterTextSplitter, so long files can be embedded and
searched effectively.
"""

from typing import List

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from config import CHUNK_SIZE, CHUNK_OVERLAP
from utils import get_logger

logger = get_logger(__name__)


def split_documents(documents: List[Document]) -> List[Document]:
    if not documents:
        return []

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_documents(documents)
    logger.info(
        "Split %d section(s) into %d chunk(s) (size=%d, overlap=%d).",
        len(documents), len(chunks), CHUNK_SIZE, CHUNK_OVERLAP,
    )
    return chunks
