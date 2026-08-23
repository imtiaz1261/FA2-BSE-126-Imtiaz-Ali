"""
LLM streaming adapter with RAG context injection.

`stream_llm_response` is the one function to swap out for a real provider.
It's an async generator that yields text chunks (not full messages) and
must check `cancel_event` between chunks so a stop request or client
disconnect actually halts generation instead of burning the rest of the
provider's response.

The mock implementation below needs no API key and lets you develop/test
the whole streaming + stop-generation pipeline end-to-end. Swap the body
for a real call when you're ready â€” an example Anthropic integration is
sketched in the comment at the bottom.
"""
import asyncio
import json
import random
import re
from collections.abc import AsyncGenerator
from types import SimpleNamespace
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas_chat import ChatMessage
from app.services.retrieval import hybrid_search

# ---- Mock implementation (default, no API key required) -----------------------

_MOCK_RESPONSES = [
    "Here's a summary of what I understood from your message:\n\n"
    "1. You want a **clear, well-structured** answer.\n"
    "2. Code should be properly formatted.\n"
    "3. Math should render nicely, e.g. $E = mc^2$.\n\n"
    "Here's a small Python example:\n\n"
    "```python\n"
    "def greet(name: str) -> str:\n"
    "    return f\"Hello, {name}!\"\n\n"
    "print(greet(\"world\"))\n"
    "```\n\n"
    "And a quick comparison table:\n\n"
    "| Approach | Speed | Complexity |\n"
    "|---|---|---|\n"
    "| Brute force | Slow | Low |\n"
    "| Dynamic programming | Fast | Medium |\n\n"
    "Let me know if you'd like me to go deeper on any part of this.",
]


class MockLLMClient:
    """Minimal async client used by features that need a non-streaming LLM call.

    The app runs in mock mode by default, so memory extraction must not require
    an API key or a provider SDK merely to import the FastAPI application.
    """

    async def create_message(
        self,
        messages: list[dict[str, str]],
        model: str = "gpt-4",
        temperature: float = 0.3,
    ) -> SimpleNamespace:
        """Return an OpenAI-shaped response containing an empty extraction."""
        del messages, model, temperature
        content = json.dumps(
            {
                "facts": [],
                "rejected_facts": [],
                "summary": "Mock LLM mode: no memories were extracted.",
            }
        )
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
        )


_llm_client = MockLLMClient()


def get_llm_client() -> MockLLMClient:
    """Return the default non-streaming LLM client."""
    return _llm_client

def _tokenize(text: str) -> list[str]:
    """Rough word-ish tokenizer so streaming looks like real token output."""
    return re.findall(r"\S+\s*", text)


def _build_rag_context(retrieved_chunks: list[dict]) -> str:
    """Build context string from retrieved chunks for injection into prompt."""
    if not retrieved_chunks:
        return ""
    
    context_lines = ["Here are relevant sources:\n"]
    
    for i, chunk in enumerate(retrieved_chunks, 1):
        source_info = f"[{i}] {chunk['filename']}"
        if chunk.get('page_number'):
            source_info += f" (page {chunk['page_number']})"
        
        context_lines.append(f"\n{source_info}:")
        context_lines.append(chunk['text'][:500])  # Limit chunk preview
        context_lines.append(f"... [Relevance: {chunk['relevance_score']:.1%}]")
    
    return "\n".join(context_lines)


async def stream_llm_response(
    messages: list[ChatMessage],
    cancel_event: asyncio.Event,
    db: Optional[AsyncSession] = None,
    conversation_id: Optional[UUID] = None,
    user_id: Optional[UUID] = None,
) -> AsyncGenerator[str, None]:
    """
    Yields chunks of the assistant's reply.
    
    If RAG is enabled (db and conversation provided), retrieves relevant
    context and injects it into the system prompt.
    
    Checks `cancel_event` between every chunk so /chat/stream/{id}/stop or
    a client disconnect stops generation immediately.
    
    Args:
        messages: Conversation history
        cancel_event: Signal to cancel generation
        db: Optional database session for RAG retrieval
        conversation_id: Optional conversation ID for scoped retrieval
        user_id: Optional user ID for scoped retrieval
    """
    
    # Extract user's last message for RAG query
    user_query = ""
    if messages:
        for msg in reversed(messages):
            if msg.role == "user":
                user_query = msg.content
                break
    
    # Attempt RAG retrieval if enabled
    rag_context = ""
    retrieved_chunks = []
    
    if db and user_query and conversation_id and user_id:
        try:
            chunks = await hybrid_search(
                db,
                user_query,
                conversation_id=conversation_id,
                user_id=user_id,
                top_k=5,
            )
            retrieved_chunks = chunks
            rag_context = _build_rag_context(chunks)
        except Exception as e:
            # Log but don't fail - RAG is optional
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"RAG retrieval failed: {e}")
    
    # Build augmented messages with RAG context
    augmented_messages = messages
    if rag_context:
        # Prepend RAG context to user's question
        last_user_idx = None
        for i in range(len(messages) - 1, -1, -1):
            if messages[i].role == "user":
                last_user_idx = i
                break
        
        if last_user_idx is not None:
            augmented_messages = list(messages)
            original_content = augmented_messages[last_user_idx].content
            augmented_messages[last_user_idx] = ChatMessage(
                role="user",
                content=f"{rag_context}\n\nUser question: {original_content}"
            )
    
    # For mock, just use original messages
    reply = random.choice(_MOCK_RESPONSES)
    for token in _tokenize(reply):
        if cancel_event.is_set():
            return
        await asyncio.sleep(0.02)  # simulates provider latency between tokens
        yield token
    
    # Return citation data as final SSE event (optional, implementation depends on frontend)
    # This would be handled by the chat router returning citations alongside the message
