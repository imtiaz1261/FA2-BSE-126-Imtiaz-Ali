"""
tools/file_tool.py
--------------------
File reading tool (PDF, DOCX, TXT).

Two modes, both driven by the same tool so the agent can call it
naturally for requests like "summarize this PDF" or "what does my
notes.docx say about the budget":

  - No question given -> returns the full extracted text (used for
    whole-document summarization by the LLM).
  - Question given     -> returns only the most relevant chunks via a
    lightweight in-memory RAG lookup (rag/vector_store.py).

Files are resolved relative to config.DATA_DIR by default, or an
absolute/relative path can be given directly.
"""

from pathlib import Path

from langchain_core.tools import tool

from config import DATA_DIR, SUPPORTED_FILE_EXTENSIONS
from rag.vector_store import get_relevant_chunks, get_all_chunks
from rag.loader import FileLoadError
from utils import get_logger

logger = get_logger(__name__)

# Cap how much raw text we hand back for whole-document summarization,
# so a huge PDF doesn't blow past the LLM's context window.
_MAX_SUMMARY_CHARS = 12000


def _resolve_path(file_name: str) -> Path:
    candidate = Path(file_name)
    if candidate.is_absolute() and candidate.exists():
        return candidate

    direct = DATA_DIR / file_name
    if direct.exists():
        return direct

    # Fuzzy fallback: match by stem if the user omitted/typo'd the extension
    matches = [
        p for p in DATA_DIR.glob("*")
        if p.suffix.lower() in SUPPORTED_FILE_EXTENSIONS
        and p.stem.lower() == Path(file_name).stem.lower()
    ]
    if matches:
        return matches[0]

    raise FileLoadError(
        f"Could not find '{file_name}' in {DATA_DIR}. "
        f"Available files: {[p.name for p in DATA_DIR.glob('*') if p.suffix.lower() in SUPPORTED_FILE_EXTENSIONS]}"
    )


@tool
def read_file(file_name: str, question: str = "") -> str:
    """
    Read a PDF, DOCX, or TXT file from the documents folder.
    Use this when the user asks to summarize, read, or ask a question
    about a specific file (e.g. "summarize this PDF", "what does
    report.docx say about Q3 revenue").

    Args:
        file_name: the file's name (e.g. "report.pdf"), matched against
            the documents folder.
        question: optional -- if the user asked something specific about
            the file, pass it here to retrieve only the relevant parts
            instead of the whole document. Leave empty for a full
            summary request.
    """
    logger.info("File tool invoked: file_name=%r question=%r", file_name, question)
    try:
        file_path = _resolve_path(file_name)

        if question.strip():
            chunks = get_relevant_chunks(file_path, question)
            if not chunks:
                return f"No relevant content found in '{file_path.name}' for that question."
            labeled = []
            for chunk in chunks:
                loc = chunk.metadata.get("page") or chunk.metadata.get("paragraph")
                label = f"[{file_path.name}" + (f", loc {loc}" if loc else "") + "]"
                labeled.append(f"{label}\n{chunk.page_content}")
            return "\n\n".join(labeled)

        chunks = get_all_chunks(file_path)
        full_text = "\n\n".join(c.page_content for c in chunks)
        truncated = full_text[:_MAX_SUMMARY_CHARS]
        note = ""
        if len(full_text) > _MAX_SUMMARY_CHARS:
            note = "\n\n[Note: document truncated for length; this covers the beginning of the file.]"
        return f"Content of {file_path.name}:\n\n{truncated}{note}"

    except FileLoadError as exc:
        logger.warning("File tool error: %s", exc)
        return f"Error: {exc}"
