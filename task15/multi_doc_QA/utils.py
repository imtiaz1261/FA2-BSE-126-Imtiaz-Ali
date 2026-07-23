"""
utils.py
--------
Shared utility helpers: logging setup and small validation functions
used across the pipeline (loader -> splitter -> embeddings -> vector
store -> retriever -> qa_chain).
"""

import logging
import sys

from config import LOG_FILE


def get_logger(name: str) -> logging.Logger:
    """
    Create (or fetch) a configured logger that writes to both the
    console and a shared log file.

    Every module in the project calls this once at import time:
        logger = get_logger(__name__)

    Parameters
    ----------
    name : str
        Typically __name__ of the calling module.

    Returns
    -------
    logging.Logger
    """
    logger = logging.getLogger(name)

    # Avoid attaching duplicate handlers if the logger already exists
    # (this can happen when modules are re-imported, e.g. in notebooks).
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler
    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    logger.propagate = False
    return logger


def is_non_empty_text(text: str) -> bool:
    """Return True if text contains at least one non-whitespace character."""
    return bool(text and text.strip())


def clean_query(query: str) -> str:
    """
    Validate and normalize a user query.

    Raises
    ------
    ValueError
        If the query is empty or whitespace only.
    """
    if not is_non_empty_text(query):
        raise ValueError("Query cannot be empty. Please ask a real question.")
    return query.strip()