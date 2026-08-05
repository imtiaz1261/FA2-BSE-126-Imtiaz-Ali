"""
Prompt management — Phase 6 + Phase 9/10.

Centralizes how conversation history becomes the `messages` list sent
to the LLM.  Phase 9/10 adds `build_rag_messages` which prepends
retrieved document chunks into the context window and injects a
citation instruction into the system prompt.

Public API
----------
  build_messages(history, new_user_content, mode)
      Plain conversational path (Chat / Research / Agent modes).

  build_rag_messages(history, new_user_content, chunks)
      Knowledge (RAG) path — injects retrieved chunks as a numbered
      context block and instructs the model to cite by [Doc N, p. X].
"""

from __future__ import annotations

from typing import TYPE_CHECKING, List

from app.core.config import settings
from app.models.message import Message, MessageRole

if TYPE_CHECKING:
    from app.services.vector_retrieval import RetrievedChunk

# ---------------------------------------------------------------------------
# System prompts per mode
# ---------------------------------------------------------------------------

_RAG_SYSTEM_SUFFIX = (
    "\n\nYou have been given a set of numbered document excerpts as context."
    " Answer the user's question using ONLY the provided context."
    " Cite each piece of information as [Doc N] or [Doc N, p. X] where N is"
    " the excerpt number and X is the page number."
    " If the context does not contain enough information to answer, say so"
    " clearly rather than guessing."
)

MODE_SYSTEM_PROMPTS = {
    "Chat": settings.LLM_SYSTEM_PROMPT,
    "Knowledge (RAG)": settings.LLM_SYSTEM_PROMPT + _RAG_SYSTEM_SUFFIX,
    "Research": (
        settings.LLM_SYSTEM_PROMPT
        + " You can research topics using web search (wired in Phase 13)."
    ),
    "Agent": (
        settings.LLM_SYSTEM_PROMPT
        + " You can use tools to complete multi-step tasks (wired in Phase 11-12)."
    ),
}


# ---------------------------------------------------------------------------
# Plain conversational path
# ---------------------------------------------------------------------------


def build_messages(
    history: list[Message],
    new_user_content: str,
    mode: str = "Chat",
) -> list[dict]:
    """
    Turns persisted Message rows + the new user message into the
    OpenAI-style `messages` list, trimmed to the most recent N turns
    per LLM_MAX_HISTORY_MESSAGES so prompts don't grow unbounded.
    """
    system_prompt = MODE_SYSTEM_PROMPTS.get(mode, settings.LLM_SYSTEM_PROMPT)
    messages: list[dict] = [{"role": "system", "content": system_prompt}]

    trimmed = history[-settings.LLM_MAX_HISTORY_MESSAGES :]
    for msg in trimmed:
        if msg.role == MessageRole.SYSTEM:
            continue
        messages.append({"role": msg.role.value, "content": msg.content})

    messages.append({"role": "user", "content": new_user_content})
    return messages


# ---------------------------------------------------------------------------
# RAG path — Phase 9/10
# ---------------------------------------------------------------------------


def _format_context_block(chunks: List["RetrievedChunk"]) -> str:
    """
    Renders retrieved chunks as a numbered reference block that the LLM
    can cite by number.

    Example output:
        [Doc 1] (research_paper.pdf, p. 3, score: 0.91)
        Deep learning models have achieved...

        [Doc 2] (notes.txt, p. 1, score: 0.87)
        The transformer architecture was introduced...
    """
    lines: list[str] = []
    for i, chunk in enumerate(chunks, start=1):
        page_info = f", p. {chunk.page_number}" if chunk.page_number else ""
        header = (
            f"[Doc {i}] ({chunk.document_name}{page_info},"
            f" score: {chunk.score:.2f}, method: {chunk.retrieval_method})"
        )
        lines.append(header)
        lines.append(chunk.content.strip())
        lines.append("")  # blank line between excerpts
    return "\n".join(lines).strip()


def build_rag_messages(
    history: list[Message],
    new_user_content: str,
    chunks: List["RetrievedChunk"],
) -> list[dict]:
    """
    RAG-aware message builder.  Injects the retrieved chunks as a
    context block in a system-level message immediately before the user
    turn, so the LLM sees:

        [system]  RAG-augmented system prompt
        [system]  --- Retrieved context ---
                  [Doc 1] ...
                  [Doc 2] ...
        [user/assistant history turns]
        [user]    current question

    Returns the same OpenAI-style list as build_messages.
    """
    system_prompt = MODE_SYSTEM_PROMPTS["Knowledge (RAG)"]
    messages: list[dict] = [{"role": "system", "content": system_prompt}]

    # Inject context block as a second system message
    if chunks:
        context_block = _format_context_block(chunks)
        messages.append(
            {
                "role": "system",
                "content": f"--- Retrieved context ---\n\n{context_block}",
            }
        )

    # History
    trimmed = history[-settings.LLM_MAX_HISTORY_MESSAGES :]
    for msg in trimmed:
        if msg.role == MessageRole.SYSTEM:
            continue
        messages.append({"role": msg.role.value, "content": msg.content})

    # Current user turn
    messages.append({"role": "user", "content": new_user_content})
    return messages


# ---------------------------------------------------------------------------
# Citation extraction helper — Phase 10
# ---------------------------------------------------------------------------


def extract_citations(
    answer: str, chunks: List["RetrievedChunk"]
) -> List[dict]:
    """
    Parse [Doc N] references from the LLM's answer and return a list of
    citation dicts that the frontend can render in the citations panel.

    Each citation dict:
        {
            "ref":           "[Doc 1]",
            "document_name": "paper.pdf",
            "page_number":   3,
            "score":         0.91,
            "snippet":       "first 200 chars of the chunk...",
        }
    """
    import re

    cited: list[dict] = []
    seen: set[int] = set()

    for match in re.finditer(r"\[Doc\s+(\d+)\]", answer):
        idx = int(match.group(1)) - 1  # convert to 0-based
        if idx in seen or idx < 0 or idx >= len(chunks):
            continue
        seen.add(idx)
        c = chunks[idx]
        cited.append(
            {
                "ref": f"[Doc {idx + 1}]",
                "document_name": c.document_name,
                "page_number": c.page_number,
                "score": round(c.score, 3),
                "snippet": c.content[:200].strip() + ("…" if len(c.content) > 200 else ""),
            }
        )

    return cited
