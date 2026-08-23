"""Tests for the chunking module."""

import pytest

from app.chunking.chunker import chunk_documents
from app.core.exceptions import ChunkingError
from app.loaders.base import LoadedDocument


def _doc(text: str, **metadata) -> LoadedDocument:
    return LoadedDocument(content=text, metadata={"filename": "sample.txt", **metadata})


def test_chunk_documents_splits_long_text():
    long_text = "Sentence about topic A. " * 200  # comfortably longer than one chunk
    documents = [_doc(long_text)]

    chunks = chunk_documents(documents, chunk_size=200, chunk_overlap=20, document_name="sample.txt")

    assert len(chunks) > 1
    for chunk in chunks:
        assert chunk.content.strip()
        assert chunk.metadata["document_name"] == "sample.txt"
        assert chunk.metadata["chunk_id"] == chunk.chunk_id


def test_chunk_documents_short_text_produces_one_chunk():
    documents = [_doc("Just one short sentence.")]

    chunks = chunk_documents(documents, chunk_size=500, chunk_overlap=50, document_name="sample.txt")

    assert len(chunks) == 1
    assert chunks[0].metadata["chunk_index"] == 0


def test_chunk_documents_rejects_overlap_larger_than_size():
    documents = [_doc("some text")]

    with pytest.raises(ChunkingError):
        chunk_documents(documents, chunk_size=100, chunk_overlap=100, document_name="sample.txt")


def test_chunk_documents_preserves_page_metadata():
    documents = [_doc("Page one content.", page=1), _doc("Page two content.", page=2)]

    chunks = chunk_documents(documents, chunk_size=500, chunk_overlap=50, document_name="sample.pdf")

    pages = {chunk.metadata["page"] for chunk in chunks}
    assert pages == {1, 2}
