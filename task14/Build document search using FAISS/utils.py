"""
utils.py
---------
Shared helper functions used across ingest.py, search.py, and app.py:
    - logging setup
    - folder / file validation with clear, actionable error messages
    - discovering supported files in the data/ folder
    - pretty-printing search results to the terminal

Keeping these in one place avoids duplicating error-handling logic in
every module (DRY) and makes the CLI output consistent everywhere.
"""

from __future__ import annotations

import logging
import os
from typing import List

# File extensions this project knows how to load (see ingest.py)
SUPPORTED_EXTENSIONS = {".pdf", ".txt"}


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """
    Configure and return a project-wide logger with a clean, readable
    format. Call this once near the start of any entry-point script
    (app.py / ingest.py / search.py).
    """
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )
    return logging.getLogger("semantic-search")


def validate_data_folder(data_dir: str) -> None:
    """
    Ensure the documents folder exists and is not empty.

    Raises:
        FileNotFoundError: if the folder does not exist at all.
        ValueError: if the folder exists but contains no files.
    """
    if not os.path.isdir(data_dir):
        raise FileNotFoundError(
            f"Documents folder not found: '{data_dir}'. "
            f"Create it and add .pdf / .txt files before running ingest.py."
        )

    entries = [f for f in os.listdir(data_dir) if os.path.isfile(os.path.join(data_dir, f))]
    if not entries:
        raise ValueError(
            f"Documents folder '{data_dir}' is empty. "
            f"Add at least one .pdf or .txt file and try again."
        )


def get_supported_files(data_dir: str, logger: logging.Logger | None = None) -> List[str]:
    """
    Return a sorted list of full file paths for all supported documents
    (.pdf, .txt) inside `data_dir`. Any unsupported file types are
    logged as warnings and skipped, rather than crashing the pipeline.

    Raises:
        ValueError: if no supported files are found after filtering.
    """
    validate_data_folder(data_dir)
    logger = logger or logging.getLogger("semantic-search")

    supported, skipped = [], []
    for filename in sorted(os.listdir(data_dir)):
        filepath = os.path.join(data_dir, filename)
        if not os.path.isfile(filepath):
            continue
        ext = os.path.splitext(filename)[1].lower()
        if ext in SUPPORTED_EXTENSIONS:
            supported.append(filepath)
        else:
            skipped.append(filename)

    if skipped:
        logger.warning(
            "Skipping %d unsupported file(s): %s (only .pdf and .txt are supported)",
            len(skipped),
            ", ".join(skipped),
        )

    if not supported:
        raise ValueError(
            f"No supported documents (.pdf / .txt) found in '{data_dir}'. "
            f"Found only unsupported types: {skipped}"
        )

    return supported


def validate_query(query: str) -> str:
    """
    Basic validation for a user's search query.

    Raises:
        ValueError: if the query is empty, whitespace-only, or too short
        to produce a meaningful search.
    """
    if query is None:
        raise ValueError("Query cannot be None.")
    cleaned = query.strip()
    if not cleaned:
        raise ValueError("Query cannot be empty. Please type a search question.")
    if len(cleaned) < 2:
        raise ValueError("Query is too short. Please provide a more descriptive search.")
    return cleaned


def print_banner(title: str) -> None:
    """Print a simple section banner to the terminal."""
    print("\n" + "=" * 64)
    print(f" {title}")
    print("=" * 64)


def print_search_results(query: str, results: list) -> None:
    """
    Pretty-print a list of search result dicts, each expected to have:
        rank, source, page, chunk_id, score, content

    If `results` is empty, prints the required fallback message:
        "No relevant information found."
    """
    print(f"\nQuery: {query}")
    print("-" * 64)

    if not results:
        print("No relevant information found.")
        return

    for r in results:
        page_display = r["page"] if r["page"] is not None else "N/A"
        print(f"\n[Result #{r['rank']}]")
        print(f"  Document       : {r['source']}")
        print(f"  Page           : {page_display}")
        print(f"  Chunk ID       : {r['chunk_id']}")
        print(f"  Similarity     : {r['score']:.4f}")
        print(f"  Retrieved Text : {r['content']}")