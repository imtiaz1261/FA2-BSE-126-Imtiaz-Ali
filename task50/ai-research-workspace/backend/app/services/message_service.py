"""Message persistence — reading/writing conversation turns."""

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.conversation import Conversation
from app.models.message import Message, MessageRole

logger = logging.getLogger(__name__)


def list_messages(db: Session, conversation_id: uuid.UUID) -> list[Message]:
    stmt = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
    )
    return list(db.scalars(stmt).all())


def add_message(db: Session, conversation_id: uuid.UUID, role: MessageRole, content: str) -> Message:
    message = Message(conversation_id=conversation_id, role=role, content=content)
    db.add(message)

    # Bump the conversation's updated_at so the sidebar's "most recent first" ordering stays fresh.
    conversation = db.get(Conversation, conversation_id)
    if conversation is not None:
        conversation.title = _maybe_auto_title(conversation, role, content)

    db.commit()
    db.refresh(message)
    logger.info("Added %s message to conversation %s", role.value, conversation_id)
    return message


def _maybe_auto_title(conversation: Conversation, role: MessageRole, content: str) -> str:
    """Auto-titles a fresh 'New Conversation' from the first user message."""
    if conversation.title == "New Conversation" and role == MessageRole.USER:
        title = content.strip().splitlines()[0][:60]
        return title or conversation.title
    return conversation.title
