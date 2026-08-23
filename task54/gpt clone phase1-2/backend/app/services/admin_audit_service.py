"""
Admin audit logging service.

Tracks all sensitive admin actions for compliance and security auditing.
"""
import logging
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models_admin import AdminAuditLog

logger = logging.getLogger(__name__)


class AdminAuditService:
    """Service for logging admin actions."""

    @staticmethod
    async def log_action(
        db: AsyncSession,
        admin_user_id: UUID,
        action: str,
        target_user_id: Optional[UUID] = None,
        reason: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> AdminAuditLog:
        """
        Log an admin action to audit trail.

        Args:
            db: Database session
            admin_user_id: Admin user performing action
            action: Action name (e.g., USER_SUSPENDED, REFUND_ISSUED)
            target_user_id: User being acted upon (if applicable)
            reason: Human-readable reason for action
            metadata: Additional structured data about the action

        Returns:
            Created audit log entry

        Raises:
            Exception: If logging fails
        """
        try:
            audit_log = AdminAuditLog(
                admin_user_id=admin_user_id,
                target_user_id=target_user_id,
                action=action,
                reason=reason,
                metadata=metadata or {},
            )

            db.add(audit_log)
            await db.commit()
            await db.refresh(audit_log)

            logger.info(
                f"Audit: {action} by {admin_user_id} "
                f"on user {target_user_id}: {reason}"
            )

            return audit_log

        except Exception as e:
            logger.error(f"Failed to log admin action: {e}")
            raise

    # Action name constants for consistency
    USER_VIEWED = "USER_VIEWED"
    USER_SUSPENDED = "USER_SUSPENDED"
    USER_UNSUSPENDED = "USER_UNSUSPENDED"
    USER_BANNED = "USER_BANNED"
    PLAN_CHANGED = "PLAN_CHANGED"
    REFUND_ISSUED = "REFUND_ISSUED"
    MODERATION_APPROVED = "MODERATION_APPROVED"
    MODERATION_BANNED = "MODERATION_BANNED"
