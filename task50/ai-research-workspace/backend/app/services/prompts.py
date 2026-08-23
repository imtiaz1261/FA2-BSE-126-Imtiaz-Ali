"""
Prompt management.

Centralizes how conversation history becomes the `messages` list sent
to the LLM — system prompt selection, history trimming, and message
role mapping all live here so both the streaming and non-streaming
paths (and later, RAG/agent modes) build prompts the same way.
"""

from app.core.config import settings
from app.models.message import Message, MessageRole

MODE_SYSTEM_PROMPTS = {
    "Chat": settings.LLM_SYSTEM_PROMPT,
    "Knowledge (RAG)": (
        settings.LLM_SYSTEM_PROMPT
        + " You have access to the user's uploaded documents for context (wired in Phase 9)."
    ),
    "Research": (
        settings.LLM_SYSTEM_PROMPT + " You can research topics using web search (wired in Phase 13)."
    ),
    "Agent": (
        settings.LLM_SYSTEM_PROMPT + " You can use tools to complete multi-step tasks (wired in Phase 11-12)."
    ),
}


def build_messages(history: list[Message], new_user_content: str, mode: str = "Chat") -> list[dict]:
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
