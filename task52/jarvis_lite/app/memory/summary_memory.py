"""
Summary Memory implementation — summarizes older conversations and keeps recent context.

Useful for longer conversations where token budget is a concern.
"""

import logging
import uuid
from typing import Any, Dict, List, Optional

from app.memory.base import BaseMemory, ConversationContext, Message

logger = logging.getLogger(__name__)


class ConversationSummaryMemory(BaseMemory):
    """
    Keeps recent messages and summarizes older ones.
    
    Strategy:
    - Keep last N "recent_messages" in full detail
    - Summarize everything older than that into a summary string
    - Include summary in context for LLM
    """

    def __init__(
        self,
        recent_messages: int = 5,
        summary_summarizer: Optional[callable] = None,
        conversation_id: Optional[str] = None,
    ) -> None:
        """
        Initialize summary memory.
        
        Args:
            recent_messages: Number of recent messages to keep in full
            summary_summarizer: Optional callable to summarize messages
            conversation_id: Optional ID for this conversation
        """
        self.recent_messages = recent_messages
        self.conversation_id = conversation_id or str(uuid.uuid4())
        self._messages: List[Message] = []
        self._summary: Optional[str] = None
        self._summary_count = 0
        self.summary_summarizer = summary_summarizer or self._default_summarizer
        logger.info(f"Initialized ConversationSummaryMemory with recent_messages={recent_messages}")

    def add_message(self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Add a message and update summary if needed."""
        msg = Message(role=role, content=content, metadata=metadata or {})
        self._messages.append(msg)
        
        # If we have more than recent_messages, summarize the oldest ones
        if len(self._messages) > self.recent_messages:
            self._update_summary()
        
        logger.debug(f"Added {role} message. Recent: {len(self._recent_messages())}, Summary: {bool(self._summary)}")

    def get_context(self) -> ConversationContext:
        """Return context with summary + recent messages."""
        recent = self._recent_messages()
        token_count = sum(len(m.content) for m in recent) // 4
        
        if self._summary:
            token_count += len(self._summary) // 4
        
        context = ConversationContext(
            conversation_id=self.conversation_id,
            messages=recent,
            summary=self._summary,
            context_tokens=token_count,
        )
        logger.debug(f"Retrieved context: {len(recent)} recent messages, summary={bool(self._summary)}")
        return context

    def get_summary(self) -> Optional[str]:
        """Return the conversation summary."""
        return self._summary

    def clear(self) -> None:
        """Clear all messages and summary."""
        self._messages.clear()
        self._summary = None
        self._summary_count = 0
        logger.info("Cleared all messages and summary")

    def _recent_messages(self) -> List[Message]:
        """Get the most recent N messages."""
        return self._messages[-self.recent_messages:]

    def _update_summary(self) -> None:
        """Summarize older messages."""
        # Keep only recent messages in _messages, move older to summary
        to_summarize = self._messages[:-self.recent_messages]
        self._messages = self._messages[-self.recent_messages:]
        
        if to_summarize:
            new_summary = self.summary_summarizer(to_summarize)
            if self._summary:
                self._summary = f"{self._summary}\n\n[Previous summary continues]\n{new_summary}"
            else:
                self._summary = new_summary
            self._summary_count += 1
            logger.info(f"Updated summary (iteration {self._summary_count}, summarized {len(to_summarize)} messages)")

    @staticmethod
    def _default_summarizer(messages: List[Message]) -> str:
        """Default simple summarizer."""
        if not messages:
            return ""
        
        summary_parts = []
        for msg in messages:
            # Take first 100 chars of each message as a simple summary
            snippet = msg.content[:100].replace("\n", " ")
            summary_parts.append(f"{msg.role}: {snippet}...")
        
        return "\n".join(summary_parts)

    def __len__(self) -> int:
        """Return number of recent messages."""
        return len(self._recent_messages())

    def __repr__(self) -> str:
        return f"ConversationSummaryMemory(recent={len(self._recent_messages())}, summary={'yes' if self._summary else 'no'})"
