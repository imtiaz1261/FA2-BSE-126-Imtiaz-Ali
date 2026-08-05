"""Conversation router — backs the Phase 5 sidebar (create/list/rename/delete)."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.conversation import ConversationCreate, ConversationOut, ConversationUpdate
from app.services import conversation_service

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("", response_model=list[ConversationOut])
def list_conversations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ConversationOut]:
    conversations = conversation_service.list_conversations(db, current_user.id)
    return [ConversationOut.model_validate(c) for c in conversations]


@router.post("", response_model=ConversationOut, status_code=status.HTTP_201_CREATED)
def create_conversation(
    data: ConversationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ConversationOut:
    conversation = conversation_service.create_conversation(db, current_user.id, data)
    return ConversationOut.model_validate(conversation)


@router.patch("/{conversation_id}", response_model=ConversationOut)
def rename_conversation(
    conversation_id: uuid.UUID,
    data: ConversationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ConversationOut:
    conversation = conversation_service.rename_conversation(db, current_user.id, conversation_id, data)
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return ConversationOut.model_validate(conversation)


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(
    conversation_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    deleted = conversation_service.delete_conversation(db, current_user.id, conversation_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
