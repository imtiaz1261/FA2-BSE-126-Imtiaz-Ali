"""
Buffer Memory implementation — keeps the last N messages in memory.

Simple, fast, and effective for short conversations.
"""

import logging
import uuid
from typing import Any, Dict, List, Optional

from app.memory.base import BaseMemory, ConversationContext, Message

logger = logging.getLogger(__name__)


class ConversationBufferMemory(BaseMemory):
    """Keeps the last N messages in memory (FIFO)."""

    def __init__(self, max_messages: int = 10, conversation_id: Optional[str] = None) -> None:
        """
        Initialize buffer memory.
        
        Args:
            max_messages: Maximum number of messages to keep
            conversation_id: Optional ID for this conversation (auto-generated if not provided)
        """
        self.max_messages = max_messages
        self.conversation_id = conversation_id or str(uuid.uuid4())
        self._messages: List[Message] = []
        logger.info(f"Initialized ConversationBufferMemory with max_messages={max_messages}")

    def add_message(self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Add a message, removing oldest if we exceed max_messages."""
        msg = Message(role=role, content=content, metadata=metadata or {})
        self._messages.append(msg)
        
        # Remove oldest message if we exceed the limit
        if len(self._messages) > self.max_messages:
            removed = self._messages.pop(0)
            logger.debug(f"Removed oldest message: {removed.role} ({len(removed.content)} chars)")
        
        logger.debug(f"Added {role} message ({len(content)} chars). Total: {len(self._messages)}")

    def get_context(self) -> ConversationContext:
        """Return all messages in the buffer."""
        # Calculate approximate token count (rough estimate: 1 token ≈ 4 chars)
        token_count = sum(len(m.content) for m in self._messages) // 4
        
        context = ConversationContext(
            conversation_id=self.conversation_id,
            messages=self._messages.copy(),
            context_tokens=token_count,
        )
        logger.debug(f"Retrieved context with {len(self._messages)} messages (~{token_count} tokens)")
        return context

    def get_summary(self) -> Optional[str]:
        """Buffer memory doesn't provide summaries."""
        return None

    def clear(self) -> None:
        """Clear all messages."""
        self._messages.clear()
        logger.info("Cleared all messages from buffer memory")

    def __len__(self) -> int:
        """Return number of messages in buffer."""
        return len(self._messages)

    def __repr__(self) -> str:
        return f"ConversationBufferMemory(messages={len(self._messages)}/{self.max_messages})"
