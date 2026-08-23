"""
Admin billing management API endpoints.

Provides:
- Plan changes
- Refunds
- Stripe operations
"""
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin_dependencies import require_admin
from app.database import get_db
from app.models import User
from app.schemas_admin import (
    ChangePlanRequest,
    ChangePlanResponse,
    RefundRequest,
    RefundResponse,
)
from app.services.admin_audit_service import AdminAuditService
from app.services.admin_billing_service import AdminBillingService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin/billing", tags=["Admin Billing"])


@router.post("/users/{user_id}/plan", response_model=ChangePlanResponse)
async def change_user_plan(
    user_id: UUID,
    payload: ChangePlanRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Change a user's subscription plan.

    For paid plans, synchronizes with Stripe.
    For free plan, cancels Stripe subscription.

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

        if result.get("success"):
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


@router.post("/users/{user_id}/refund", response_model=RefundResponse)
async def issue_refund(
    user_id: UUID,
    payload: RefundRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Issue a refund for a payment.

    Supports both full and partial refunds.
    Processes refund via Stripe.

    Path Parameters:
    - user_id: User ID (UUID)

    Request Body:
    - payment_intent_id: Stripe payment intent ID
    - amount: Amount in USD (None for full refund)
    - reason: Reason for refund

    Returns:
    - success: True if refund processed
    - refund_id: Stripe refund ID
    - status: Refund status
    - amount: Refunded amount
    - message: Human-readable message
    """
    try:
        billing_service = AdminBillingService()
        result = await billing_service.issue_refund(
            db,
            user_id,
            payload.payment_intent_id,
            payload.amount,
            payload.reason,
        )

        if result.get("success"):
            # Log action
            await AdminAuditService.log_action(
                db,
                admin_user_id=admin.id,
                action=AdminAuditService.REFUND_ISSUED,
                target_user_id=user_id,
                reason=payload.reason,
                metadata={
                    "payment_intent_id": payload.payment_intent_id,
                    "amount": payload.amount,
                    "refund_id": result.get("refund_id"),
                },
            )

        return result

    except Exception as e:
        logger.error(f"Failed to issue refund: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to issue refund",
        )
