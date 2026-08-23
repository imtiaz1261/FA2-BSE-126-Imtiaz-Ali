"""Settings and model selection endpoints.

Endpoints:
- GET/PATCH /settings — user preferences (theme, font size, language, instructions)
- GET /models — available LLM models
- GET /conversations/{id}/model — get selected model for conversation
- PATCH /conversations/{id}/model — select model for conversation
- GET /usage — daily message usage for free tier rate limiting
- POST /settings/export — async data export (triggers job, returns status)
- DELETE /conversations — bulk delete all conversations
- DELETE /account — delete user account
"""

import json
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models import (
    AvailableModel,
    Conversation,
    ConversationModel,
    DataExportJob,
    Message,
    MessageUsage,
    User,
    UserSettings,
)
from app.schemas_settings import (
    AvailableModelResponse,
    ClearConversationsRequest,
    DeleteAccountRequest,
    ExportJobRequest,
    ExportJobResponse,
    ModelSelectionRequest,
    ModelSelectorResponse,
    SettingsPatchRequest,
    SettingsPreferences,
    SettingsResponse,
    UsageResponse,
)
from app.security import verify_password, hash_password

router = APIRouter(prefix="/settings", tags=["settings"])
models_router = APIRouter(prefix="/models", tags=["models"])
usage_router = APIRouter(prefix="/usage", tags=["usage"])
conversations_router = APIRouter(prefix="/conversations", tags=["conversations"])

FREE_TIER_MESSAGE_LIMIT = 20  # Messages per day for free tier users


# ---- Settings (GET/PATCH) -------------------------------------------------------


@router.get("", response_model=SettingsResponse)
async def get_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get user settings."""
    result = await db.execute(
        select(UserSettings).where(UserSettings.user_id == current_user.id)
    )
    user_settings = result.scalar_one_or_none()

    if user_settings is None:
        # Return default settings if not yet created
        return SettingsResponse(
            preferences=SettingsPreferences()
        )

    return SettingsResponse(
        preferences=SettingsPreferences(**user_settings.preferences)
    )


@router.patch("", response_model=SettingsResponse)
async def patch_settings(
    payload: SettingsPatchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update user settings."""
    result = await db.execute(
        select(UserSettings).where(UserSettings.user_id == current_user.id)
    )
    user_settings = result.scalar_one_or_none()

    if user_settings is None:
        # Create new settings record
        user_settings = UserSettings(
            user_id=current_user.id,
            preferences=payload.preferences.model_dump() if payload.preferences else {},
        )
        db.add(user_settings)
    else:
        # Update existing settings
        if payload.preferences:
            user_settings.preferences = payload.preferences.model_dump()

    await db.commit()
    await db.refresh(user_settings)

    return SettingsResponse(
        preferences=SettingsPreferences(**user_settings.preferences)
    )


# ---- Available Models (GET) -------------------------------------------------------


@models_router.get("", response_model=list[AvailableModelResponse])
async def list_available_models(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List available LLM models."""
    result = await db.execute(
        select(AvailableModel).where(AvailableModel.is_active == True).order_by(AvailableModel.tier)
    )
    models = result.scalars().all()
    return [AvailableModelResponse.model_validate(m) for m in models]


# ---- Conversation Model Selection -------------------------------------------------------


@conversations_router.get("/{conversation_id}/model", response_model=ModelSelectorResponse)
async def get_conversation_model(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get selected model for a conversation."""
    # Verify conversation ownership
    conv_result = await db.execute(
        select(Conversation).where(
            and_(
                Conversation.id == conversation_id,
                Conversation.user_id == current_user.id,
            )
        )
    )
    conversation = conv_result.scalar_one_or_none()
    if conversation is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found.")

    # Get selected model for this conversation
    model_result = await db.execute(
        select(ConversationModel).where(ConversationModel.conversation_id == conversation_id)
    )
    conversation_model = model_result.scalar_one_or_none()

    # Get all available models
    available_result = await db.execute(
        select(AvailableModel).where(AvailableModel.is_active == True).order_by(AvailableModel.tier)
    )
    available_models = available_result.scalars().all()

    selected_model = None
    if conversation_model:
        selected_model = AvailableModelResponse.model_validate(conversation_model.model)

    return ModelSelectorResponse(
        conversation_id=str(conversation_id),
        selected_model_id=str(conversation_model.model_id) if conversation_model else None,
        selected_model=selected_model,
        available_models=[AvailableModelResponse.model_validate(m) for m in available_models],
    )


@conversations_router.patch("/{conversation_id}/model", response_model=ModelSelectorResponse)
async def set_conversation_model(
    conversation_id: uuid.UUID,
    payload: ModelSelectionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Select model for a conversation."""
    # Verify conversation ownership
    conv_result = await db.execute(
        select(Conversation).where(
            and_(
                Conversation.id == conversation_id,
                Conversation.user_id == current_user.id,
            )
        )
    )
    conversation = conv_result.scalar_one_or_none()
    if conversation is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found.")

    # Verify model exists and is active
    model_result = await db.execute(
        select(AvailableModel).where(
            and_(
                AvailableModel.id == uuid.UUID(payload.model_id),
                AvailableModel.is_active == True,
            )
        )
    )
    model = model_result.scalar_one_or_none()
    if model is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Model not found or inactive.")

    # Delete existing model association
    await db.execute(
        delete(ConversationModel).where(ConversationModel.conversation_id == conversation_id)
    )

    # Create new model association
    conversation_model = ConversationModel(
        conversation_id=conversation_id,
        model_id=uuid.UUID(payload.model_id),
    )
    db.add(conversation_model)
    await db.commit()

    # Refresh and return
    available_result = await db.execute(
        select(AvailableModel).where(AvailableModel.is_active == True).order_by(AvailableModel.tier)
    )
    available_models = available_result.scalars().all()

    return ModelSelectorResponse(
        conversation_id=str(conversation_id),
        selected_model_id=str(model.id),
        selected_model=AvailableModelResponse.model_validate(model),
        available_models=[AvailableModelResponse.model_validate(m) for m in available_models],
    )


# ---- Usage Tracking -------------------------------------------------------


@usage_router.get("", response_model=UsageResponse)
async def get_usage(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get daily message usage for free tier rate limiting."""
    today = datetime.now(timezone.utc).date()

    result = await db.execute(
        select(MessageUsage).where(
            and_(
                MessageUsage.user_id == current_user.id,
                MessageUsage.date == today,
            )
        )
    )
    usage = result.scalar_one_or_none()

    used = usage.message_count if usage else 0
    limit = FREE_TIER_MESSAGE_LIMIT
    remaining = max(0, limit - used)

    return UsageResponse(
        used=used,
        limit=limit,
        remaining=remaining,
    )


# ---- Data Export -------------------------------------------------------


@router.post("/export", response_model=ExportJobResponse)
async def export_data(
    payload: ExportJobRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Initiate async data export job.
    Returns immediately with job status. User receives email with download link
    when export completes (link expires in 7 days).
    """
    # Create export job record
    job = DataExportJob(
        user_id=current_user.id,
        status="pending",
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # TODO: Trigger async task to:
    # 1. Export all conversations, messages, settings as JSON
    # 2. Create signed download URL
    # 3. Update job record with URL and expires_at
    # 4. Send email to user with link

    return ExportJobResponse(
        job_id=str(job.id),
        status=job.status,
        download_url=job.download_url,
        expires_at=job.expires_at.isoformat() if job.expires_at else None,
    )


# ---- Clear All Conversations -------------------------------------------------------


@conversations_router.delete("")
async def clear_all_conversations(
    payload: ClearConversationsRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete all conversations for the user.
    Requires typed confirmation: user must submit "I understand"
    """
    if payload.confirmation != "I understand":
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Confirmation text must be 'I understand'",
        )

    # Delete all conversations (cascades to messages)
    await db.execute(
        delete(Conversation).where(Conversation.user_id == current_user.id)
    )
    await db.commit()

    return {"message": "All conversations deleted"}


# ---- Delete Account -------------------------------------------------------


@router.delete("/account")
async def delete_account(
    payload: DeleteAccountRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete user account and all associated data.
    Requires either:
    - Password (for password-authenticated users)
    - Typed confirmation matching email (for OAuth users)
    """
    # Verify confirmation
    valid_confirmation = (
        payload.confirmation == "I understand"
        or payload.confirmation == current_user.email
    )

    if not valid_confirmation:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Invalid confirmation. Must type 'I understand' or your email address.",
        )

    # For password-authenticated users, verify password
    if current_user.hashed_password and payload.password:
        if not verify_password(payload.password, current_user.hashed_password):
            raise HTTPException(
                status.HTTP_401_UNAUTHORIZED,
                "Invalid password",
            )
    elif current_user.hashed_password and not payload.password:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Password required for password-authenticated accounts",
        )

    # Delete user (cascades to all related data)
    await db.delete(current_user)
    await db.commit()

    return {"message": "Account deleted"}


# ---- Message Usage Increment (internal) -------------------------------------------------------


async def increment_message_usage(
    user_id: uuid.UUID,
    db: AsyncSession,
):
    """Increment message count for today. Called after each user message."""
    today = datetime.now(timezone.utc).date()

    result = await db.execute(
        select(MessageUsage).where(
            and_(
                MessageUsage.user_id == user_id,
                MessageUsage.date == today,
            )
        )
    )
    usage = result.scalar_one_or_none()

    if usage is None:
        usage = MessageUsage(
            user_id=user_id,
            date=today,
            message_count=1,
        )
        db.add(usage)
    else:
        usage.message_count += 1

    await db.commit()
