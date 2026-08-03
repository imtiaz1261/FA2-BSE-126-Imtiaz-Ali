"""
models/chat.py
==============
Pydantic schemas for the chat conversation layer.

ChatMessage      — a single turn (user or assistant)
ChatSession      — a named conversation with full history
ConversationHistory — the sidebar list of past sessions
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Single message
# ---------------------------------------------------------------------------
class ChatMessage(BaseModel):
    """Represents one turn in the conversation."""

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique message identifier",
    )
    role: str = Field(
        description="'user' | 'assistant' | 'system'",
    )
    content: str = Field(
        description="Message text (Markdown supported)",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC time the message was created",
    )
    image_attached: bool = Field(
        default=False,
        description="True when this user turn included an image upload",
    )
    image_filename: Optional[str] = Field(
        default=None,
        description="Original filename of the attached image",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary extra data (tokens_used, model, latency_ms, …)",
    )

    # ------------------------------------------------------------------
    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        allowed = {"user", "assistant", "system"}
        if v not in allowed:
            raise ValueError(f"role must be one of {allowed}, got '{v}'")
        return v

    # ------------------------------------------------------------------
    @property
    def is_user(self) -> bool:
        return self.role == "user"

    @property
    def is_assistant(self) -> bool:
        return self.role == "assistant"

    @property
    def formatted_time(self) -> str:
        """Return HH:MM format for display."""
        return self.timestamp.strftime("%H:%M")

    @property
    def formatted_datetime(self) -> str:
        """Return full datetime string for tooltip."""
        return self.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")

    def to_openai_dict(self) -> Dict[str, Any]:
        """
        Convert to the format expected by the OpenAI Chat Completions API.
        Images are handled separately in vision_service.py.
        """
        return {"role": self.role, "content": self.content}


# ---------------------------------------------------------------------------
# Chat session (one document / conversation)
# ---------------------------------------------------------------------------
class ChatSession(BaseModel):
    """
    A complete conversation session tied to one uploaded image.
    """

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
    )
    title: str = Field(
        default="New Chat",
        description="Auto-generated or user-set session title",
    )
    messages: List[ChatMessage] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    image_filename: Optional[str] = Field(default=None)
    document_type: Optional[str] = Field(default=None)
    total_tokens_used: int = Field(default=0)

    # ------------------------------------------------------------------
    def add_message(self, message: ChatMessage) -> None:
        """Append a message and refresh updated_at."""
        self.messages.append(message)
        self.updated_at = datetime.now(timezone.utc)

    def add_user_message(
        self,
        content: str,
        image_attached: bool = False,
        image_filename: Optional[str] = None,
    ) -> ChatMessage:
        """Convenience: create and append a user turn."""
        msg = ChatMessage(
            role="user",
            content=content,
            image_attached=image_attached,
            image_filename=image_filename,
        )
        self.add_message(msg)
        return msg

    def add_assistant_message(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ChatMessage:
        """Convenience: create and append an assistant turn."""
        msg = ChatMessage(
            role="assistant",
            content=content,
            metadata=metadata or {},
        )
        self.add_message(msg)
        # Track token usage
        tokens = (metadata or {}).get("tokens_used", 0)
        self.total_tokens_used += tokens
        return msg

    def get_openai_history(self) -> List[Dict[str, Any]]:
        """
        Return the message history in OpenAI API format.
        Excludes the system message (injected by llm_service) and any
        messages that carry binary image data.
        """
        return [m.to_openai_dict() for m in self.messages if m.role != "system"]

    @property
    def message_count(self) -> int:
        return len([m for m in self.messages if m.role != "system"])

    @property
    def last_message(self) -> Optional[ChatMessage]:
        return self.messages[-1] if self.messages else None

    def clear(self) -> None:
        """Remove all messages (keeps session metadata)."""
        self.messages.clear()
        self.updated_at = datetime.now(timezone.utc)

    def auto_title(self) -> str:
        """
        Generate a short title from the first user message.
        Falls back to image filename or 'New Chat'.
        """
        for msg in self.messages:
            if msg.is_user and len(msg.content) > 3:
                return msg.content[:40].strip() + ("…" if len(msg.content) > 40 else "")
        if self.image_filename:
            return self.image_filename[:30]
        return "New Chat"


# ---------------------------------------------------------------------------
# Sidebar history entry (lightweight reference)
# ---------------------------------------------------------------------------
class ConversationSummary(BaseModel):
    """Lightweight snapshot shown in the sidebar history list."""

    session_id: str
    title: str
    image_filename: Optional[str] = None
    document_type: Optional[str] = None
    message_count: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Conversation history (sidebar collection)
# ---------------------------------------------------------------------------
class ConversationHistory(BaseModel):
    """Ordered list of past sessions (most-recent first)."""

    sessions: List[ConversationSummary] = Field(default_factory=list)

    def add(self, session: ChatSession) -> None:
        summary = ConversationSummary(
            session_id=session.id,
            title=session.auto_title(),
            image_filename=session.image_filename,
            document_type=session.document_type,
            message_count=session.message_count,
            created_at=session.created_at,
            updated_at=session.updated_at,
        )
        # Insert at front, remove duplicates
        self.sessions = [s for s in self.sessions if s.session_id != session.id]
        self.sessions.insert(0, summary)
        # Cap at 20 entries
        self.sessions = self.sessions[:20]

    def remove(self, session_id: str) -> None:
        self.sessions = [s for s in self.sessions if s.session_id != session_id]

    def clear(self) -> None:
        self.sessions.clear()
