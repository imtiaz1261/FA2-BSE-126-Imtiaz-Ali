"""
Admin content moderation API endpoints.

Provides:
- Moderation queue management
- Flag review and details
- Approve / ban decisions
"""
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin_dependencies import require_admin
from app.database import get_db
from app.models import User
from app.schemas_admin import (
    ApproveModerationRequest,
    ApproveModerationResponse,
    BanModeratedUserRequest,
    BanModeratedUserResponse,
    ModerationFlagResponse,
    ModerationDetailsResponse,
)
from app.services.admin_audit_service import AdminAuditService
from app.services.moderation_service import ModerationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin/moderation", tags=["Admin Moderation"])


@router.get("")
async def get_moderation_queue(
    status: str | None = Query(None),
    severity: str | None = Query(None),
    category: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get moderation queue with filters.

    Query Parameters:
    - status: Filter by status (pending, approved, banned, dismissed)
    - severity: Filter by severity (low, medium, high, critical)
    - category: Filter by category
    - page: Page number (1-indexed)
    - page_size: Results per page (1-100)

    Returns:
    - items: List of moderation flags
    - page, page_size, total: Pagination info
    """
    try:
        result = await ModerationService.get_moderation_queue(
            db,
            status=status,
            severity=severity,
            category=category,
            page=page,
            page_size=page_size,
        )

        return result

    except Exception as e:
        logger.error(f"Failed to get moderation queue: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve moderation queue",
        )


@router.get("/{flag_id}")
async def get_flag_details(
    flag_id: UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> ModerationDetailsResponse:
    """
    Get complete moderation flag details.

    Includes:
    - Flag information
    - User details
    - Conversation metadata
    - Recent messages

    Path Parameters:
    - flag_id: Flag ID (UUID)
    """
    try:
        details = await ModerationService.get_flag_details(db, flag_id)

        if not details:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Flag not found",
            )

        return ModerationDetailsResponse(**details)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get flag details: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve flag details",
        )


@router.post("/{flag_id}/approve", response_model=ApproveModerationResponse)
async def approve_moderation_flag(
    flag_id: UUID,
    payload: ApproveModerationRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Approve a moderation flag.

    Marks flag as approved (content deemed acceptable).

    Path Parameters:
    - flag_id: Flag ID (UUID)

    Request Body:
    - note: Admin notes on the decision

    Returns:
    - success: True if approved
    - status: "approved"
    - message: Human-readable message
    """
    try:
        result = await ModerationService.approve_flag(
            db,
            flag_id,
            admin.id,
            payload.note,
        )

        if result.get("success"):
            # Log action
            await AdminAuditService.log_action(
                db,
                admin_user_id=admin.id,
                action=AdminAuditService.MODERATION_APPROVED,
                reason=payload.note,
                metadata={"flag_id": str(flag_id)},
            )

        return result

    except Exception as e:
        logger.error(f"Failed to approve flag: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to approve flag",
        )


@router.post("/{flag_id}/ban", response_model=BanModeratedUserResponse)
async def ban_from_moderation(
    flag_id: UUID,
    payload: BanModeratedUserRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Ban a user based on moderation flag.

    Marks flag as resolved and permanently bans the user.

    Path Parameters:
    - flag_id: Flag ID (UUID)

    Request Body:
    - reason: Reason for ban

    Returns:
    - success: True if user banned
    - status: "banned"
    - user_banned: True if user was banned
    - message: Human-readable message
    """
    try:
        result = await ModerationService.ban_from_flag(
            db,
            flag_id,
            admin.id,
            payload.reason,
        )

        if result.get("success"):
            # Log action
            await AdminAuditService.log_action(
                db,
                admin_user_id=admin.id,
                action=AdminAuditService.MODERATION_BANNED,
                reason=payload.reason,
                metadata={"flag_id": str(flag_id)},
            )

        return result

    except Exception as e:
        logger.error(f"Failed to ban user from moderation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to ban user",
        )
