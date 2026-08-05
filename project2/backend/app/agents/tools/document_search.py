"""
Document search tool — Phase 12.

Wraps the existing hybrid RAG retrieval pipeline (Phase 9/10) as an
agent tool so the LangGraph agent can search the user's uploaded
documents on demand.

The tool is initialised with the SQLAlchemy Session and user_id at
agent-run time (injected by the tool registry), so it is NOT a
pure-function tool — it is a callable object.  The tool registry
handles injection transparently.
"""

import logging
import uuid
from typing import Optional

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

_TOP_K = 5
_SNIPPET_LEN = 400  # chars shown per chunk in the result string


def _format_results(chunks) -> str:
    if not chunks:
        return "No relevant documents found."

    lines = []
    for i, c in enumerate(chunks, start=1):
        page = f", p. {c.page_number}" if c.page_number else ""
        lines.append(
            f"**[Chunk {i}]** {c.document_name}{page} "
            f"(score: {c.score:.2f}, method: {c.retrieval_method})"
        )
        lines.append(c.content[:_SNIPPET_LEN].strip())
        if len(c.content) > _SNIPPET_LEN:
            lines.append("…")
        lines.append("")
    return "\n".join(lines).strip()


async def document_search(
    query: str,
    db: Session,
    user_id: uuid.UUID,
    top_k: int = _TOP_K,
) -> str:
    """
    Search the user's uploaded documents for content relevant to the query.

    Args:
        query: The natural-language search query.
        db: SQLAlchemy session (injected by tool registry).
        user_id: The requesting user's ID (injected by tool registry).
        top_k: Number of chunks to retrieve (default 5).

    Returns:
        A Markdown-formatted string of matching document excerpts.
    """
    try:
        from app.services.hybrid_retrieval import hybrid_retrieve

        chunks = await hybrid_retrieve(
            db=db,
            user_id=user_id,
            query=query,
            top_k=top_k,
        )
        return _format_results(chunks)
    except Exception as exc:
        logger.exception("Document search failed: %s", exc)
        return f"Document search error: {exc}"
