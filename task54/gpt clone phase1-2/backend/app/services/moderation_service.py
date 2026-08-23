"""
Content moderation service.

Handles:
- Flagging conversations for review
- Moderation queue management
- Approval and banning decisions
- User actions from moderation
"""
import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Conversation, Message, User, UserStatus
from app.models_admin import ModerationFlag

logger = logging.getLogger(__name__)


class ModerationService:
    """Service for content moderation."""

    @staticmethod
    async def flag_conversation(
        db: AsyncSession,
        conversation_id: UUID,
        user_id: UUID,
        category: str,
        severity: str,
        reason: Optional[str] = None,
        message_id: Optional[UUID] = None,
        metadata: Optional[dict] = None,
    ) -> dict:
        """
        Flag a conversation for moderation review.

        Args:
            db: Database session
            conversation_id: Conversation to flag
            user_id: User who owns the conversation
            category: Flag category (e.g., self_harm, violence, harassment)
            severity: Severity level (low, medium, high, critical)
            reason: Detailed reason for flag
            message_id: Specific message being flagged (optional)
            metadata: Additional structured data

        Returns:
            Dict with flag details
        """
        try:
            flag = ModerationFlag(
                conversation_id=conversation_id,
                message_id=message_id,
                user_id=user_id,
                category=category,
                severity=severity,
                reason=reason,
                status="pending",
                metadata=metadata or {},
            )

            db.add(flag)
            await db.commit()
            await db.refresh(flag)

            logger.info(
                f"Flagged conversation {conversation_id} by user {user_id}: "
                f"{category} ({severity})"
            )

            return {
                "success": True,
                "flag_id": flag.id,
                "status": "pending",
                "message": "Conversation flagged for review",
            }

        except Exception as e:
            logger.error(f"Failed to flag conversation: {e}")
            return {"success": False, "message": "Failed to flag conversation"}

    @staticmethod
    async def get_moderation_queue(
        db: AsyncSession,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        category: Optional[str] = None,
        page: int = 1,
        page_size: int = 25,
    ) -> dict:
        """
        Get moderation queue with filters.

        Args:
            db: Database session
            status: Filter by status (pending, approved, banned, dismissed)
            severity: Filter by severity
            category: Filter by category
            page: Page number (1-indexed)
            page_size: Results per page

        Returns:
            Dict with queue items and pagination
        """
        try:
            # Build query
            stmt = select(ModerationFlag)

            conditions = []

            if status:
                conditions.append(ModerationFlag.status == status)
            else:
                # Default to pending
                conditions.append(ModerationFlag.status == "pending")

            if severity:
                conditions.append(ModerationFlag.severity == severity)

            if category:
                conditions.append(ModerationFlag.category == category)

            if conditions:
                stmt = stmt.where(and_(*conditions))

            # Get total count
            count_stmt = select(func.count(ModerationFlag.id))
            if conditions:
                count_stmt = count_stmt.where(and_(*conditions))
            total = await db.scalar(count_stmt) or 0

            # Apply sorting and pagination
            stmt = stmt.order_by(ModerationFlag.created_at.desc())
            offset = (page - 1) * page_size
            stmt = stmt.offset(offset).limit(page_size)

            results = await db.execute(stmt)
            flags = results.scalars().all()

            items = [
                {
                    "id": flag.id,
                    "conversation_id": flag.conversation_id,
                    "user_id": flag.user_id,
                    "category": flag.category,
                    "severity": flag.severity,
                    "reason": flag.reason,
                    "status": flag.status,
                    "created_at": flag.created_at,
                    "reviewed_at": flag.reviewed_at,
                }
                for flag in flags
            ]

            return {
                "items": items,
                "page": page,
                "page_size": page_size,
                "total": total,
            }

        except Exception as e:
            logger.error(f"Failed to get moderation queue: {e}")
            return {"items": [], "page": page, "page_size": page_size, "total": 0}

    @staticmethod
    async def get_flag_details(
        db: AsyncSession,
        flag_id: UUID,
    ) -> dict:
        """
        Get complete flag details including conversation and messages.

        Args:
            db: Database session
            flag_id: Flag ID to get details for

        Returns:
            Dict with flag and conversation details
        """
        try:
            # Get flag
            flag = await db.get(ModerationFlag, flag_id)
            if not flag:
                return {}

            # Get conversation
            conversation = await db.get(Conversation, flag.conversation_id)
            if not conversation:
                return {}

            # Get user
            user = await db.get(User, flag.user_id)

            # Get recent messages
            messages_stmt = select(Message).where(
                Message.conversation_id == flag.conversation_id
            ).order_by(Message.created_at.desc()).limit(10)

            msg_results = await db.execute(messages_stmt)
            messages = msg_results.scalars().all()

            return {
                "flag": {
                    "id": flag.id,
                    "conversation_id": flag.conversation_id,
                    "user_id": flag.user_id,
                    "category": flag.category,
                    "severity": flag.severity,
                    "reason": flag.reason,
                    "status": flag.status,
                    "created_at": flag.created_at,
                    "reviewed_at": flag.reviewed_at,
                },
                "user_email": user.email if user else "unknown",
                "user_name": user.name if user else None,
                "conversation_title": conversation.title,
                "message_count": len(messages),
                "recent_messages": [
                    {
                        "id": msg.id,
                        "role": msg.role.value,
                        "content": msg.content[:500],  # Truncate
                        "created_at": msg.created_at,
                    }
                    for msg in messages
                ],
            }

        except Exception as e:
            logger.error(f"Failed to get flag details: {e}")
            return {}

    @staticmethod
    async def approve_flag(
        db: AsyncSession,
        flag_id: UUID,
        admin_user_id: UUID,
        note: Optional[str] = None,
    ) -> dict:
        """
        Approve a moderation flag (determine content was acceptable).

        Args:
            db: Database session
            flag_id: Flag ID to approve
            admin_user_id: Admin user reviewing
            note: Admin notes

        Returns:
            Dict with success status
        """
        try:
            flag = await db.get(ModerationFlag, flag_id)
            if not flag:
                return {"success": False, "message": "Flag not found"}

            flag.status = "approved"
            flag.reviewed_by = admin_user_id
            flag.reviewed_at = datetime.utcnow()

            if note:
                flag.metadata["admin_note"] = note

            await db.commit()

            logger.info(f"Approved moderation flag {flag_id}")

            return {
                "success": True,
                "status": "approved",
                "message": "Flag marked as approved",
            }

        except Exception as e:
            logger.error(f"Failed to approve flag: {e}")
            return {"success": False, "message": "Failed to approve flag"}

    @staticmethod
    async def ban_from_flag(
        db: AsyncSession,
        flag_id: UUID,
        admin_user_id: UUID,
        reason: str = "",
    ) -> dict:
        """
        Ban a user based on moderation flag.

        Marks flag as banned and bans the user account.

        Args:
            db: Database session
            flag_id: Flag ID
            admin_user_id: Admin user taking action
            reason: Reason for ban

        Returns:
            Dict with success status
        """
        try:
            flag = await db.get(ModerationFlag, flag_id)
            if not flag:
                return {"success": False, "message": "Flag not found"}

            # Update flag
            flag.status = "banned"
            flag.reviewed_by = admin_user_id
            flag.reviewed_at = datetime.utcnow()
            flag.metadata["ban_reason"] = reason

            # Ban the user
            user = await db.get(User, flag.user_id)
            if user:
                user.status = UserStatus.banned
                user.is_active = False

            await db.commit()

            logger.info(
                f"Banned user {flag.user_id} from moderation flag {flag_id}: {reason}"
            )

            return {
                "success": True,
                "status": "banned",
                "user_banned": True,
                "message": f"User banned and flag marked as resolved",
            }

        except Exception as e:
            logger.error(f"Failed to ban user from flag: {e}")
            return {"success": False, "message": "Failed to ban user"}
