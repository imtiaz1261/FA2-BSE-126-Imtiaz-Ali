"""
Admin user management API endpoints.

Provides user search, details, and management actions:
- Search and filter users
- Get user details
- Suspend / unsuspend
- Ban
- Change plan
"""
import logging
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin_dependencies import require_admin
from app.database import get_db
from app.models import User
from app.schemas_admin import (
    BanUserRequest,
    BanUserResponse,
    ChangePlanRequest,
    ChangePlanResponse,
    SuspendUserRequest,
    SuspendUserResponse,
    UserDetailResponse,
    UsersListResponse,
)
from app.services.admin_audit_service import AdminAuditService
from app.services.admin_billing_service import AdminBillingService
from app.services.admin_user_service import AdminUserService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin/users", tags=["Admin Users"])


@router.get("")
async def list_users(
    search: str | None = Query(None),
    plan: str | None = Query(None),
    status: str | None = Query(None),
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    sort: str = Query("created_at"),
    order: str = Query("desc"),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> UsersListResponse:
    """
    Search and filter users.

    Query Parameters:
    - search: Search by email or name
    - plan: Filter by plan (free, plus, pro)
    - status: Filter by status (active, suspended, banned)
    - start_date: Filter by signup date (ISO format)
    - end_date: Filter by signup date (ISO format)
    - page: Page number (1-indexed)
    - page_size: Results per page (1-100)
    - sort: Sort field (created_at, email, last_active_at)
    - order: Sort order (asc, desc)

    Returns:
    - items: List of users
    - page, page_size, total: Pagination info
    """
    try:
        # Parse dates
        start_dt = None
        end_dt = None

        if start_date:
            try:
                start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
            except ValueError:
                pass

        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
            except ValueError:
                pass

        result = await AdminUserService.search_users(
            db,
            search=search,
            plan=plan,
            status=status,
            start_date=start_dt,
            end_date=end_dt,
            page=page,
            page_size=page_size,
            sort=sort,
            order=order,
        )

        return UsersListResponse(**result)

    except Exception as e:
        logger.error(f"Failed to list users: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve users",
        )


@router.get("/{user_id}")
async def get_user_details(
    user_id: UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> UserDetailResponse:
    """
    Get complete user details.

    Includes:
    - Account info
    - Subscription details
    - Usage metrics
    - Recent activity

    Path Parameters:
    - user_id: User ID (UUID)
    """
    try:
        # Log view action
        await AdminAuditService.log_action(
            db,
            admin_user_id=admin.id,
            action=AdminAuditService.USER_VIEWED,
            target_user_id=user_id,
        )

        details = await AdminUserService.get_user_details(db, user_id)

        if not details:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        return UserDetailResponse(**details)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get user details: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user details",
        )


@router.post("/{user_id}/suspend", response_model=SuspendUserResponse)
async def suspend_user(
    user_id: UUID,
    payload: SuspendUserRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Suspend a user account.

    Suspended users cannot login but account data is preserved.

    Path Parameters:
    - user_id: User ID (UUID)

    Request Body:
    - reason: Reason for suspension

    Returns:
    - success: True if suspended
    - status: "suspended"
    - message: Human-readable message
    """
    try:
        result = await AdminUserService.suspend_user(db, user_id, payload.reason)

        # Log action
        await AdminAuditService.log_action(
            db,
            admin_user_id=admin.id,
            action=AdminAuditService.USER_SUSPENDED,
            target_user_id=user_id,
            reason=payload.reason,
        )

        return result

    except Exception as e:
        logger.error(f"Failed to suspend user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to suspend user",
        )


@router.post("/{user_id}/unsuspend", response_model=SuspendUserResponse)
async def unsuspend_user(
    user_id: UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Unsuspend a user account.

    Path Parameters:
    - user_id: User ID (UUID)

    Returns:
    - success: True if unsuspended
    - status: "active"
    - message: Human-readable message
    """
    try:
        result = await AdminUserService.unsuspend_user(db, user_id)

        # Log action
        await AdminAuditService.log_action(
            db,
            admin_user_id=admin.id,
            action=AdminAuditService.USER_UNSUSPENDED,
            target_user_id=user_id,
        )

        return result

    except Exception as e:
        logger.error(f"Failed to unsuspend user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to unsuspend user",
        )


@router.post("/{user_id}/ban", response_model=BanUserResponse)
async def ban_user(
    user_id: UUID,
    payload: BanUserRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Permanently ban a user account.

    Banned users cannot login and account is locked.

    Path Parameters:
    - user_id: User ID (UUID)

    Request Body:
    - reason: Reason for ban

    Returns:
    - success: True if banned
    - status: "banned"
    - message: Human-readable message
    """
    try:
        result = await AdminUserService.ban_user(db, user_id, payload.reason)

        # Log action
        await AdminAuditService.log_action(
            db,
            admin_user_id=admin.id,
            action=AdminAuditService.USER_BANNED,
            target_user_id=user_id,
            reason=payload.reason,
        )

        return result

    except Exception as e:
        logger.error(f"Failed to ban user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to ban user",
        )


@router.post("/{user_id}/plan", response_model=ChangePlanResponse)
async def change_user_plan(
    user_id: UUID,
    payload: ChangePlanRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Change a user's subscription plan.

    For paid plans, synchronizes with Stripe.
    For free plan, cancels Stripe subscription appropriately.

    Path Parameters:
    - user_id: User ID (UUID)

    Request Body:
    - plan: Target plan (free, plus, pro)

    Returns:
    - success: True if plan changed
    - new_plan: New plan name
    - message: Human-readable message
    """
    try:
        billing_service = AdminBillingService()
        result = await billing_service.change_user_plan(
            db,
            user_id,
            payload.plan,
        )

        # Log action
        await AdminAuditService.log_action(
            db,
            admin_user_id=admin.id,
            action=AdminAuditService.PLAN_CHANGED,
            target_user_id=user_id,
            metadata={"new_plan": payload.plan},
        )

        return result

    except Exception as e:
        logger.error(f"Failed to change user plan: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to change user plan",
        )
