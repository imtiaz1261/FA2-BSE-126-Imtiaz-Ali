"""Conversation business logic. Every lookup is scoped to the owning user."""

import logging
import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.conversation import Conversation
from app.schemas.conversation import ConversationCreate, ConversationUpdate

logger = logging.getLogger(__name__)


def list_conversations(db: Session, user_id: uuid.UUID) -> list[Conversation]:
    stmt = (
        select(Conversation)
        .where(Conversation.user_id == user_id)
        .order_by(Conversation.updated_at.desc())
    )
    return list(db.scalars(stmt).all())


def get_conversation(db: Session, user_id: uuid.UUID, conversation_id: uuid.UUID) -> Optional[Conversation]:
    stmt = select(Conversation).where(
        Conversation.id == conversation_id, Conversation.user_id == user_id
    )
    return db.scalars(stmt).first()


def create_conversation(db: Session, user_id: uuid.UUID, data: ConversationCreate) -> Conversation:
    conversation = Conversation(user_id=user_id, title=data.title)
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    logger.info("Created conversation %s for user %s", conversation.id, user_id)
    return conversation


def rename_conversation(
    db: Session, user_id: uuid.UUID, conversation_id: uuid.UUID, data: ConversationUpdate
) -> Optional[Conversation]:
    conversation = get_conversation(db, user_id, conversation_id)
    if conversation is None:
        return None
    conversation.title = data.title
    db.commit()
    db.refresh(conversation)
    return conversation


def delete_conversation(db: Session, user_id: uuid.UUID, conversation_id: uuid.UUID) -> bool:
    conversation = get_conversation(db, user_id, conversation_id)
    if conversation is None:
        return False
    db.delete(conversation)
    db.commit()
    logger.info("Deleted conversation %s for user %s", conversation_id, user_id)
    return True
