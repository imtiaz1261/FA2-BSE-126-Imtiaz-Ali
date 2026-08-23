"""
FastAPI routes for Memory & Personalization.

Endpoints:
- GET /memory/items - List all user's memories
- GET /memory/items/{id} - Get specific memory
- POST /memory/items - Create new memory
- PUT /memory/items/{id} - Update memory
- DELETE /memory/items/{id} - Delete memory
- GET /memory/settings - Get memory settings
- PUT /memory/settings - Update memory settings
- POST /memory/extract - Trigger manual extraction
- GET /memory/stats - Get memory statistics
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models import User
from app.models_memory import (
    MemoryCategory,
    UserMemoryItem,
    UserMemorySettings,
    MemoryExtractionLog,
)
from app.services.memory_extraction import MemoryExtractionService
from app.services.memory_retrieval import MemoryRetrievalService

router = APIRouter(prefix="/memory", tags=["memory"])

# Initialize services
extraction_service = MemoryExtractionService()
retrieval_service = MemoryRetrievalService()


# ============================================================================
# Schemas (simplified inline for brevity)
# ============================================================================


class MemoryItemResponse:
    """Memory item response."""

    id: str
    fact: str
    category: str
    relevance_score: float
    created_at: str
    updated_at: str
    is_active: bool


class MemorySettingsResponse:
    """Memory settings response."""

    memory_enabled: bool
    auto_extract_enabled: bool
    max_memory_items: int
    context_injection_count: int
    retrieval_threshold: float


# ============================================================================
# Memory Items CRUD
# ============================================================================


@router.get("/items")
async def list_memories(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    category: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all user's memory items."""
    query = select(UserMemoryItem).where(UserMemoryItem.user_id == current_user.id)

    if category:
        try:
            query = query.where(UserMemoryItem.category == MemoryCategory(category))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid category: {category}")

    # Total count
    total = await db.scalar(
        select(func.count(UserMemoryItem.id)).where(
            UserMemoryItem.user_id == current_user.id
        )
    )

    # Paginated results
    items = await db.scalars(query.offset(skip).limit(limit))

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": [
            {
                "id": str(item.id),
                "fact": item.fact,
                "category": item.category.value,
                "relevance_score": item.relevance_score,
                "created_at": item.created_at.isoformat(),
                "updated_at": item.updated_at.isoformat(),
                "is_active": item.is_active,
                "source_conversation_id": str(item.source_conversation_id)
                if item.source_conversation_id
                else None,
            }
            for item in items
        ],
    }


@router.get("/items/{item_id}")
async def get_memory(
    item_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific memory item."""
    try:
        item_uuid = uuid.UUID(item_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID")

    item = await db.get(UserMemoryItem, item_uuid)

    if not item or item.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Memory not found")

    return {
        "id": str(item.id),
        "fact": item.fact,
        "category": item.category.value,
        "relevance_score": item.relevance_score,
        "created_at": item.created_at.isoformat(),
        "updated_at": item.updated_at.isoformat(),
        "is_active": item.is_active,
        "extraction_context": item.extraction_context,
        "source_conversation_id": str(item.source_conversation_id)
        if item.source_conversation_id
        else None,
    }


@router.post("/items")
async def create_memory(
    fact: str = Query(..., min_length=10, max_length=500),
    category: str = Query("other"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new memory item (manual entry)."""
    try:
        cat = MemoryCategory(category)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid category. Must be one of: {', '.join(c.value for c in MemoryCategory)}",
        )

    # Check memory limit
    settings = await db.scalar(
        select(UserMemorySettings).where(UserMemorySettings.user_id == current_user.id)
    )
    if not settings:
        settings = UserMemorySettings(user_id=current_user.id)
        db.add(settings)
        await db.commit()

    count = await db.scalar(
        select(func.count(UserMemoryItem.id)).where(
            UserMemoryItem.user_id == current_user.id
        )
    )

    if count and count >= settings.max_memory_items:
        raise HTTPException(
            status_code=400,
            detail=f"Memory limit reached ({settings.max_memory_items} items)",
        )

    item = UserMemoryItem(
        user_id=current_user.id,
        fact=fact,
        category=cat,
        relevance_score=1.0,
        is_active=True,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)

    return {
        "id": str(item.id),
        "fact": item.fact,
        "category": item.category.value,
        "created_at": item.created_at.isoformat(),
    }


@router.put("/items/{item_id}")
async def update_memory(
    item_id: str,
    fact: Optional[str] = Query(None, min_length=10, max_length=500),
    category: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a memory item."""
    try:
        item_uuid = uuid.UUID(item_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID")

    item = await db.get(UserMemoryItem, item_uuid)

    if not item or item.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Memory not found")

    if fact:
        item.fact = fact

    if category:
        try:
            item.category = MemoryCategory(category)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid category: {category}")

    if is_active is not None:
        item.is_active = is_active

    # Mark as user-edited
    from datetime import datetime

    item.user_edited_at = datetime.utcnow()

    await db.commit()
    await db.refresh(item)

    return {
        "id": str(item.id),
        "fact": item.fact,
        "category": item.category.value,
        "updated_at": item.updated_at.isoformat(),
    }


@router.delete("/items/{item_id}")
async def delete_memory(
    item_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a memory item."""
    try:
        item_uuid = uuid.UUID(item_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID")

    item = await db.get(UserMemoryItem, item_uuid)

    if not item or item.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Memory not found")

    await db.delete(item)
    await db.commit()

    return {"status": "deleted", "id": str(item.id)}


# ============================================================================
# Memory Settings
# ============================================================================


@router.get("/settings")
async def get_memory_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get user's memory settings."""
    settings = await db.scalar(
        select(UserMemorySettings).where(UserMemorySettings.user_id == current_user.id)
    )

    if not settings:
        settings = UserMemorySettings(user_id=current_user.id)
        db.add(settings)
        await db.commit()
        await db.refresh(settings)

    return {
        "memory_enabled": settings.memory_enabled,
        "auto_extract_enabled": settings.auto_extract_enabled,
        "max_memory_items": settings.max_memory_items,
        "context_injection_count": settings.context_injection_count,
        "retrieval_threshold": settings.retrieval_threshold,
        "retention_days": settings.retention_days,
        "last_extraction_at": settings.last_extraction_at.isoformat()
        if settings.last_extraction_at
        else None,
    }


@router.put("/settings")
async def update_memory_settings(
    memory_enabled: Optional[bool] = Query(None),
    auto_extract_enabled: Optional[bool] = Query(None),
    max_memory_items: Optional[int] = Query(None, ge=1, le=500),
    context_injection_count: Optional[int] = Query(None, ge=1, le=20),
    retrieval_threshold: Optional[float] = Query(None, ge=0.0, le=1.0),
    retention_days: Optional[int] = Query(None, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update user's memory settings."""
    settings = await db.scalar(
        select(UserMemorySettings).where(UserMemorySettings.user_id == current_user.id)
    )

    if not settings:
        settings = UserMemorySettings(user_id=current_user.id)
        db.add(settings)
        await db.commit()

    if memory_enabled is not None:
        settings.memory_enabled = memory_enabled
    if auto_extract_enabled is not None:
        settings.auto_extract_enabled = auto_extract_enabled
    if max_memory_items is not None:
        settings.max_memory_items = max_memory_items
    if context_injection_count is not None:
        settings.context_injection_count = context_injection_count
    if retrieval_threshold is not None:
        settings.retrieval_threshold = retrieval_threshold
    if retention_days is not None:
        settings.retention_days = retention_days

    await db.commit()
    await db.refresh(settings)

    return {
        "message": "Settings updated",
        "memory_enabled": settings.memory_enabled,
        "auto_extract_enabled": settings.auto_extract_enabled,
    }


# ============================================================================
# Extraction & Retrieval
# ============================================================================


@router.post("/extract")
async def trigger_extraction(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Manually trigger memory extraction from recent conversations.

    Useful for immediate fact discovery without waiting for scheduled job.
    """
    try:
        logs = await extraction_service.extract_from_recent_conversations(
            user_id=current_user.id, db=db, limit=5
        )

        total_extracted = sum(log.facts_extracted_count for log in logs)
        total_rejected = sum(log.facts_rejected_count for log in logs)

        return {
            "status": "extraction_complete",
            "conversations_processed": len(logs),
            "total_extracted": total_extracted,
            "total_rejected": total_rejected,
            "logs": [
                {
                    "facts_extracted": log.facts_extracted_count,
                    "facts_rejected": log.facts_rejected_count,
                    "trigger": log.trigger,
                }
                for log in logs
            ],
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_memory_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get memory statistics for user."""
    total = await db.scalar(
        select(func.count(UserMemoryItem.id)).where(
            UserMemoryItem.user_id == current_user.id
        )
    )

    by_category = {}
    items = await db.scalars(
        select(UserMemoryItem).where(UserMemoryItem.user_id == current_user.id)
    )

    for item in items:
        cat = item.category.value
        by_category[cat] = by_category.get(cat, 0) + 1

    # Latest extraction log
    latest_log = await db.scalar(
        select(MemoryExtractionLog)
        .where(MemoryExtractionLog.user_id == current_user.id)
        .order_by(MemoryExtractionLog.created_at.desc())
        .limit(1)
    )

    return {
        "total_memories": total or 0,
        "by_category": by_category,
        "latest_extraction": {
            "created_at": latest_log.created_at.isoformat(),
            "facts_extracted": latest_log.facts_extracted_count,
            "facts_rejected": latest_log.facts_rejected_count,
        }
        if latest_log
        else None,
    }
