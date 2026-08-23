"""
Memory Service — orchestrates memory management and integration with RAG pipeline.

Handles conversation lifecycle, context retrieval, and integration with LLM.
"""

import logging
from typing import Any, Dict, List, Literal, Optional

from app.config.settings import settings
from app.core.exceptions import MemoryError
from app.memory.base import BaseMemory, ConversationContext, Message
from app.memory.buffer_memory import ConversationBufferMemory
from app.memory.summary_memory import ConversationSummaryMemory

logger = logging.getLogger(__name__)


class MemoryService:
    """Manages conversation memory and context."""

    def __init__(
        self,
        memory_type: Literal["buffer", "summary"] = "buffer",
        max_context: int = 10,
        conversation_id: Optional[str] = None,
    ) -> None:
        """
        Initialize memory service.
        
        Args:
            memory_type: Type of memory ("buffer" or "summary")
            max_context: Max messages (buffer) or recent messages (summary)
            conversation_id: Optional conversation ID
        """
        self.memory_type = memory_type
        self.conversation_id = conversation_id
        
        if memory_type == "buffer":
            self._memory: BaseMemory = ConversationBufferMemory(
                max_messages=max_context,
                conversation_id=conversation_id,
            )
        elif memory_type == "summary":
            self._memory = ConversationSummaryMemory(
                recent_messages=max_context,
                conversation_id=conversation_id,
            )
        else:
            raise MemoryError(f"Unknown memory type: {memory_type}")
        
        logger.info(f"Initialized MemoryService with {memory_type} memory")

    def add_user_message(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Add user message to memory."""
        self._memory.add_message("user", content, metadata)
        logger.debug(f"Added user message ({len(content)} chars)")

    def add_assistant_message(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Add assistant message to memory."""
        self._memory.add_message("assistant", content, metadata)
        logger.debug(f"Added assistant message ({len(content)} chars)")

    def get_context(self) -> ConversationContext:
        """Get conversation context for LLM."""
        return self._memory.get_context()

    def get_context_for_prompt(self) -> List[Dict[str, str]]:
        """
        Get conversation history formatted for LLM prompt.
        
        Returns:
            List of message dicts suitable for OpenAI/Gemini API
        """
        context = self.get_context()
        messages = []
        
        # Add summary as system message if available
        if context.summary:
            messages.append({
                "role": "system",
                "content": f"Previous conversation summary:\n{context.summary}"
            })
        
        # Add recent messages
        for msg in context.messages:
            messages.append({
                "role": msg.role,
                "content": msg.content,
            })
        
        return messages

    def get_summary(self) -> Optional[str]:
        """Get conversation summary."""
        return self._memory.get_summary()

    def clear(self) -> None:
        """Clear all memory."""
        self._memory.clear()
        logger.info("Cleared memory service")

    def get_message_count(self) -> int:
        """Get number of messages in memory."""
        return len(self._memory)

    def get_last_user_message(self) -> Optional[str]:
        """Get the last user message."""
        context = self.get_context()
        for msg in reversed(context.messages):
            if msg.role == "user":
                return msg.content
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Export memory state."""
        context = self.get_context()
        return {
            "conversation_id": context.conversation_id,
            "memory_type": self.memory_type,
            "message_count": len(context.messages),
            "context_tokens": context.context_tokens,
            "summary": context.summary,
            "messages": [m.to_dict() for m in context.messages],
        }

    def __repr__(self) -> str:
        return f"MemoryService({self.memory_type}, messages={self.get_message_count()})"
