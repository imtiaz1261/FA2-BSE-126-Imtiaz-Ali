"""
Base memory classes for conversation context management.

Supports multiple memory strategies:
- BufferMemory: Keep last N messages
- SummaryMemory: Summarize old conversations, keep recent ones
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime


@dataclass
class Message:
    """A single conversation message."""
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class ConversationContext:
    """Complete conversation context for LLM processing."""
    conversation_id: str
    messages: List[Message]
    summary: Optional[str] = None
    context_tokens: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "conversation_id": self.conversation_id,
            "messages": [m.to_dict() for m in self.messages],
            "summary": self.summary,
            "context_tokens": self.context_tokens,
        }


class BaseMemory(ABC):
    """Abstract base class for memory strategies."""

    @abstractmethod
    def add_message(self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Add a message to memory."""
        raise NotImplementedError

    @abstractmethod
    def get_context(self) -> ConversationContext:
        """Retrieve conversation context for LLM."""
        raise NotImplementedError

    @abstractmethod
    def clear(self) -> None:
        """Clear all memory."""
        raise NotImplementedError

    @abstractmethod
    def get_summary(self) -> Optional[str]:
        """Get a summary of the conversation."""
        raise NotImplementedError
