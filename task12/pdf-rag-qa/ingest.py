"""
ingest.py — Loads PDFs, splits them into chunks, embeds them, and stores
them in a persistent ChromaDB vector database.

Run this once (or whenever you add/change PDFs in data/) before running
app.py to ask questions:

    python ingest.py

Pipeline:
    PDF files (data/*.pdf)
        |  PyPDFLoader reads each page as a separate Document,
        |  keeping page numbers as metadata
        v
    RecursiveCharacterTextSplitter
        |  breaks each page's text into ~1000-character chunks with
        |  200-character overlap, so context isn't lost at chunk edges
        v
    HuggingFaceEmbeddings
        |  converts each chunk of text into a numeric vector that
        |  captures its meaning (runs locally, free, no API key needed)
        v
    ChromaDB (persisted to chroma_db/)
        |  stores every (chunk, vector) pair on disk, so it only needs
        |  to be built once and can be reloaded instantly later
        v
    Ready for retriever.py / app.py to query
"""

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader
from langchain_huggingface import HuggingFaceEmbeddings

from utils import CHROMA_DIR, get_logger, validate_pdf_directory

logger = get_logger("ingest")

# Free, local embedding model — runs on your machine, no API key or cost.
# 384-dimensional vectors, a good balance of speed and quality for a
# beginner/intermediate RAG project.
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200


def load_pdfs(pdf_paths: list[str]) -> list:
    """Loads every PDF into a list of LangChain Document objects.

    PyPDFLoader creates one Document per PAGE (not per file), and
    automatically attaches metadata like {"source": "data/sample.pdf",
    "page": 3} to each one — this metadata is what lets us show source
    page numbers later when answering questions.
    """
    all_documents = []

    for path in pdf_paths:
        logger.info(f"Loading: {path}")
        loader = PyPDFLoader(path)
        documents = loader.load()
        all_documents.extend(documents)
        logger.info(f"  -> {len(documents)} page(s) loaded")

    return all_documents


def split_documents(documents: list) -> list:
    """Splits documents into ~1000-character chunks with 200-character
    overlap.

    Why chunk at all? Embedding models and LLM context windows both have
    limits, and a whole page is often too large/unfocused to embed
    meaningfully. Why overlap? Without it, a sentence that happens to
    fall right on a chunk boundary would be split in half, and neither
    resulting chunk would contain its full meaning. The 200-character
    overlap means each chunk shares some text with its neighbors, so
    ideas that span a boundary are still captured intact in at least one
    chunk.

    RecursiveCharacterTextSplitter tries splitting on paragraph breaks
    first, then sentences, then words — falling back only if it must —
    so chunks stay as semantically coherent as possible.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
    )
    chunks = splitter.split_documents(documents)
    logger.info(f"Split {len(documents)} page(s) into {len(chunks)} chunk(s)")
    return chunks


def create_vector_store(chunks: list, persist_directory: str = CHROMA_DIR) -> Chroma:
    """Embeds every chunk and stores them in a persistent ChromaDB
    collection on disk at `persist_directory`.

    Chroma.from_documents() does two things in one call: it runs each
    chunk's text through the embedding model to get a vector, then
    writes both the original text and its vector to the database. Since
    ChromaDB is configured with a persist_directory, everything is saved
    to disk automatically — no separate ".save()" call needed, and the
    next time this directory is opened, all embeddings are already there.
    """
    logger.info(f"Loading embedding model: {EMBEDDING_MODEL_NAME} (first run downloads it, ~90MB)")
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)

    logger.info(f"Embedding {len(chunks)} chunk(s) and writing to '{persist_directory}/'...")
    vector_store = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=persist_directory,
    )
    logger.info("Vector store created and persisted successfully.")
    return vector_store


def main() -> None:
    pdf_paths = validate_pdf_directory()  # raises a clear error if data/ has no PDFs
    logger.info(f"Found {len(pdf_paths)} PDF(s): {[p for p in pdf_paths]}")

    documents = load_pdfs(pdf_paths)
    chunks = split_documents(documents)
    create_vector_store(chunks)

    logger.info("Ingestion complete. You can now run: python app.py")


if __name__ == "__main__":
    main()