"""Turns a query + retrieved chunks into the messages sent to the LLM."""

from typing import Dict, List

from app.retriever.retriever import RetrievedChunk

SYSTEM_PROMPT = (
    "You are Jarvis, a precise research assistant. Answer the user's question "
    "using ONLY the numbered context below. Cite the sources you use inline "
    "as [1], [2], etc., matching the numbered blocks. If the context doesn't "
    "contain the answer, say so plainly instead of guessing."
)


def _format_context(chunks: List[RetrievedChunk]) -> str:
    blocks = []
    for i, chunk in enumerate(chunks, start=1):
        name = chunk.metadata.get("document_name", "unknown document")
        page = chunk.metadata.get("page")
        location = f"{name}, page {page}" if page else name
        blocks.append(f"[{i}] (source: {location})\n{chunk.content}")
    return "\n\n".join(blocks)


def build_prompt(query: str, retrieved_chunks: List[RetrievedChunk]) -> List[Dict[str, str]]:
    """Returns an OpenAI-style `messages` list ready for a chat completion call."""
    context = _format_context(retrieved_chunks)
    user_content = f"Context:\n\n{context}\n\nQuestion: {query}"
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]
