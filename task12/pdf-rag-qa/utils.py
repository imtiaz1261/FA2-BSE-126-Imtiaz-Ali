"""
utils.py — Shared helper functions used across the project.

Keeping validation and setup logic here (instead of duplicating it in
ingest.py, retriever.py, and app.py) means every script fails fast with a
clear error message instead of crashing deep inside a LangChain call with
a confusing stack trace.
"""

import glob
import logging
import os

from dotenv import load_dotenv

DATA_DIR = "data"
CHROMA_DIR = "chroma_db"


def get_logger(name: str) -> logging.Logger:
    """Returns a logger with consistent, readable formatting across all
    scripts in this project."""
    logger = logging.getLogger(name)
    if not logger.handlers:  # avoid duplicate handlers if called twice
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("[%(name)s] %(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


def load_environment() -> str:
    """Loads .env and validates that GROQ_API_KEY is present.

    Raises a clear, actionable error immediately if the key is missing —
    this is the "missing API key" error case from the project spec.
    """
    load_dotenv()
    api_key = os.environ.get("GROQ_API_KEY")

    if not api_key or api_key.strip() == "" or "your_api_key_here" in api_key:
        raise EnvironmentError(
            "GROQ_API_KEY is missing or not set. Create a .env file in the "
            "project root with:\n\n    GROQ_API_KEY=your_actual_key_here\n\n"
            "Get a free key at: https://console.groq.com/keys"
        )

    return api_key


def validate_pdf_directory(data_dir: str = DATA_DIR) -> list[str]:
    """Checks that at least one PDF exists in the data directory.

    This is the "missing PDF" error case from the project spec — it's
    much friendlier to fail here with a clear message than to let
    LangChain's document loader fail with an obscure I/O error later.
    """
    if not os.path.isdir(data_dir):
        raise FileNotFoundError(
            f"Data directory '{data_dir}' does not exist. Create it and add "
            f"at least one PDF file before running ingest.py."
        )

    pdf_paths = glob.glob(os.path.join(data_dir, "*.pdf"))

    if not pdf_paths:
        raise FileNotFoundError(
            f"No PDF files found in '{data_dir}/'. Add at least one .pdf "
            f"file to that folder before running ingest.py."
        )

    return pdf_paths


def validate_question(question: str) -> str:
    """Validates a user's question isn't empty/whitespace-only.

    This is the "empty question" error case from the project spec.
    """
    if question is None or question.strip() == "":
        raise ValueError("Question cannot be empty. Please type a real question.")
    return question.strip()


def validate_vector_store_exists(chroma_dir: str = CHROMA_DIR) -> None:
    """Checks the Chroma persistent directory exists and has content.

    This is the "empty vector database" error case from the project spec —
    it catches the common beginner mistake of running app.py before ever
    running ingest.py.
    """
    if not os.path.isdir(chroma_dir) or not os.listdir(chroma_dir):
        raise FileNotFoundError(
            f"No vector database found at '{chroma_dir}/'. You need to run "
            f"ingest.py first to process your PDFs before asking questions:\n\n"
            f"    python ingest.py"
        )