"""
ingest.py
-----------
Builds the FAISS vector index from documents in the data/ folder.

Pipeline:
    1. load_documents_from_folder()  - load .pdf / .txt files as LangChain
                                        Document objects (page-aware for PDFs)
    2. split_documents()             - chunk each document with
                                        RecursiveCharacterTextSplitter
                                        (chunk_size=1000, chunk_overlap=200)
    3. build_and_save_faiss_index()  - embed every chunk and store the
                                        vectors in a FAISS index, saved
                                        locally to faiss_index/

Run directly to (re)build the index:
    python ingest.py
    python ingest.py --data-dir data --index-dir faiss_index
    python ingest.py --force-fallback     # no internet? use offline embeddings
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from typing import List

from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from embeddings import get_embedding_model
from utils import get_supported_files, print_banner, setup_logging

logger = logging.getLogger("semantic-search.ingest")

DEFAULT_CHUNK_SIZE = 1000
DEFAULT_CHUNK_OVERLAP = 200


def load_documents_from_folder(data_dir: str) -> List[Document]:
    """
    Load every supported file (.pdf, .txt) in `data_dir` into a list of
    LangChain `Document` objects.

    - PDFs are loaded with PyPDFLoader, which creates ONE Document per
      page, so page numbers are preserved in `metadata["page"]`
      (0-indexed by the loader; we store it as a human-friendly 1-indexed
      value).
    - TXT files are loaded with TextLoader as a single Document (no page
      concept for plain text).

    Raises:
        FileNotFoundError / ValueError: propagated from utils.get_supported_files
        if the folder is missing or empty (handled with clear messages there).
    """
    filepaths = get_supported_files(data_dir, logger=logger)
    documents: List[Document] = []

    for filepath in filepaths:
        filename = os.path.basename(filepath)
        ext = os.path.splitext(filename)[1].lower()

        try:
            if ext == ".pdf":
                loader = PyPDFLoader(filepath)
                pdf_pages = loader.load()
                for page_doc in pdf_pages:
                    # PyPDFLoader gives 0-indexed pages; store 1-indexed for display
                    raw_page = page_doc.metadata.get("page", 0)
                    page_doc.metadata["page"] = raw_page + 1
                    page_doc.metadata["source"] = filename
                    documents.append(page_doc)

            elif ext == ".txt":
                loader = TextLoader(filepath, encoding="utf-8")
                txt_docs = loader.load()
                for doc in txt_docs:
                    doc.metadata["source"] = filename
                    doc.metadata["page"] = None  # no page concept for plain text
                    documents.append(doc)

        except Exception as exc:  # noqa: BLE001 - skip a bad file, keep going
            logger.error("Failed to load '%s': %s", filename, exc)
            continue

    if not documents:
        raise ValueError(
            f"No document content could be extracted from files in '{data_dir}'. "
            f"Check that the files are not corrupted or empty."
        )

    logger.info("Loaded %d page/document objects from %d file(s)", len(documents), len(filepaths))
    return documents


def split_documents(
    documents: List[Document],
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> List[Document]:
    """
    Split loaded documents into overlapping chunks using
    RecursiveCharacterTextSplitter, which tries to split on paragraph
    breaks first, then sentences, then words - preserving semantic
    coherence better than a naive fixed-length split.

    Each resulting chunk keeps its parent document's metadata (source
    filename, page number) and gets an additional `chunk_id` for display.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    chunks = splitter.split_documents(documents)

    for i, chunk in enumerate(chunks):
        chunk.metadata["chunk_id"] = i

    logger.info(
        "Split %d document(s) into %d chunks (chunk_size=%d, overlap=%d)",
        len(documents), len(chunks), chunk_size, chunk_overlap,
    )
    return chunks


def build_and_save_faiss_index(
    chunks: List[Document],
    embedding_model,
    index_dir: str = "faiss_index",
) -> FAISS:
    """
    Embed every chunk and build a FAISS vector index, then persist it to
    disk so it can be reloaded later without recomputation (see search.py).

    Returns:
        The in-memory FAISS vectorstore (also saved to `index_dir`).
    """
    if not chunks:
        raise ValueError("Cannot build an index from zero chunks.")

    backend_name = getattr(embedding_model, "backend", "openai")
    logger.info("Generating embeddings for %d chunks (backend=%s)...", len(chunks), backend_name)
    vectorstore = FAISS.from_documents(chunks, embedding_model)

    os.makedirs(index_dir, exist_ok=True)
    vectorstore.save_local(index_dir)
    logger.info("FAISS index saved to '%s' (%d vectors)", index_dir, vectorstore.index.ntotal)

    return vectorstore


def run_ingest_pipeline(
    data_dir: str = "data",
    index_dir: str = "faiss_index",
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    force_fallback: bool = False,
    use_openai: bool = False,
) -> FAISS:
    """Convenience wrapper that runs the full ingest pipeline end-to-end."""
    print_banner("Semantic Document Search — Index Build")

    documents = load_documents_from_folder(data_dir)
    chunks = split_documents(documents, chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    embedding_model = get_embedding_model(
        index_dir=index_dir, force_fallback=force_fallback, use_openai=use_openai
    )
    vectorstore = build_and_save_faiss_index(chunks, embedding_model, index_dir=index_dir)

    logger.info("Ingestion complete. %d chunks indexed from %d file(s).",
                len(chunks), len({d.metadata["source"] for d in documents}))
    return vectorstore


def main():
    parser = argparse.ArgumentParser(description="Build the FAISS index from documents in data/")
    parser.add_argument("--data-dir", default="data", help="Folder containing .pdf / .txt files")
    parser.add_argument(
        "--index-dir", default="faiss_index", help="Folder to save the FAISS index to")
    parser.add_argument(
        "--chunk-size", type=int, default=DEFAULT_CHUNK_SIZE, help="Chunk size in characters")
    parser.add_argument(
        "--chunk-overlap", type=int, default=DEFAULT_CHUNK_OVERLAP,
        help="Chunk overlap in characters")
    parser.add_argument(
        "--force-fallback", action="store_true",
        help="Force offline TF-IDF+SVD embeddings")
    parser.add_argument(
        "--use-openai", action="store_true",
        help="Use OpenAI embeddings instead of sentence-transformers")
    args = parser.parse_args()

    setup_logging()
    try:
        run_ingest_pipeline(
            data_dir=args.data_dir,
            index_dir=args.index_dir,
            chunk_size=args.chunk_size,
            chunk_overlap=args.chunk_overlap,
            force_fallback=args.force_fallback,
            use_openai=args.use_openai,
        )
    except (FileNotFoundError, ValueError, EnvironmentError) as exc:
        logger.error(str(exc))
        sys.exit(1)


if __name__ == "__main__":
    main()