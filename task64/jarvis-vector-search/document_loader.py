"""
document_loader.py
--------------------
Reads .txt/.md files from a directory and turns them into indexable
chunks with metadata (document id, filename, source, category, title,
chunk index).

Expected (optional) file format — a lightweight frontmatter:

    Title: My Document Title
    Category: Some Category
    ---
    Body text starts here and can span
    multiple lines / paragraphs.

If a file doesn't have this header, the filename is used as the title
and "General" as the category — plain text files work fine too.

Long documents are split into overlapping chunks (CHUNK_SIZE /
CHUNK_OVERLAP from config) so retrieval returns focused passages
rather than entire long files.
"""
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

from exceptions import DocumentLoadError, ValidationError
from logger import get_logger

logger = get_logger(__name__)

SUPPORTED_EXTENSIONS = {".txt", ".md"}


@dataclass
class Chunk:
    id: str
    text: str
    metadata: Dict[str, Any] = field(default_factory=dict)


def _parse_frontmatter(raw: str) -> (str, str, str):
    """Returns (title, category, body). Falls back gracefully if no frontmatter present."""
    match = re.match(r"^Title:\s*(.+?)\nCategory:\s*(.+?)\n-{3,}\n(.*)$", raw, re.DOTALL)
    if match:
        title, category, body = match.groups()
        return title.strip(), category.strip(), body.strip()
    return "", "", raw.strip()


def _chunk_text(text: str, chunk_size: int, overlap: int) -> List[str]:
    """Simple, dependency-free character-based chunker with overlap.
    Splits on paragraph/sentence boundaries where possible to avoid
    cutting words mid-sentence."""
    text = text.strip()
    if len(text) <= chunk_size:
        return [text] if text else []

    chunks = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + chunk_size, n)
        if end < n:
            # try to break at the last sentence boundary within the window
            boundary = text.rfind(". ", start, end)
            if boundary != -1 and boundary > start + int(chunk_size * 0.5):
                end = boundary + 1
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= n:
            break
        start = max(end - overlap, start + 1)
    return chunks


def load_documents(
    directory: str,
    chunk_size: int = 800,
    chunk_overlap: int = 100,
) -> List[Chunk]:
    """
    Load every supported text file in `directory`, parse title/category
    if present, chunk long content, and return a flat list of Chunk
    objects ready to be embedded and indexed.
    """
    dir_path = Path(directory)
    if not dir_path.exists() or not dir_path.is_dir():
        raise DocumentLoadError(f"Documents directory not found: {directory}")

    files = sorted(
        p for p in dir_path.iterdir() if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
    )
    if not files:
        raise DocumentLoadError(
            f"No .txt/.md files found in '{directory}'. Add documents before indexing."
        )

    chunks: List[Chunk] = []
    for file_path in files:
        try:
            raw = file_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.warning(f"Skipping unreadable file '{file_path.name}': {e}")
            continue

        if not raw.strip():
            logger.warning(f"Skipping empty file '{file_path.name}'")
            continue

        title, category, body = _parse_frontmatter(raw)
        if not title:
            title = file_path.stem.replace("_", " ").replace("-", " ").title()
        if not category:
            category = "General"

        pieces = _chunk_text(body, chunk_size, chunk_overlap)
        for i, piece in enumerate(pieces):
            chunk_id = f"{file_path.stem}::chunk{i}"
            metadata = {
                "doc_id": file_path.stem,
                "filename": file_path.name,
                "source": str(file_path),
                "title": title,
                "category": category,
                "chunk_index": i,
                "num_chunks": len(pieces),
            }
            chunks.append(Chunk(id=chunk_id, text=piece, metadata=metadata))

    if not chunks:
        raise DocumentLoadError(f"No indexable content produced from files in '{directory}'.")

    logger.info(f"Loaded {len(files)} file(s) -> {len(chunks)} chunk(s) from '{directory}'.")
    return chunks


def validate_chunks(chunks: List[Chunk]) -> None:
    if not chunks:
        raise ValidationError("No chunks to index.")
    seen_ids = set()
    for c in chunks:
        if not c.text or not c.text.strip():
            raise ValidationError(f"Chunk '{c.id}' has empty text.")
        if c.id in seen_ids:
            raise ValidationError(f"Duplicate chunk id detected: '{c.id}'.")
        seen_ids.add(c.id)
