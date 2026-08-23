"""
Admin user management service.

Handles:
- User search and filtering
- User details aggregation
- User suspension/unsuspension
- User banning
- Activity tracking
"""
import logging
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Conversation, Message, User, UserStatus
from app.models_billing import Subscription
from app.models_billing import SubscriptionPlan, SubscriptionStatus
from app.services.usage_meter import UsageMeterService

logger = logging.getLogger(__name__)


class AdminUserService:
    """Service for admin user management operations."""

    @staticmethod
    async def search_users(
        db: AsyncSession,
        search: Optional[str] = None,
        plan: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 25,
        sort: str = "created_at",
        order: str = "desc",
    ) -> dict:
        """
        Search and filter users.

        Args:
            db: Database session
            search: Search by email or name
            plan: Filter by subscription plan
            status: Filter by account status
            start_date: Filter by signup date (start)
            end_date: Filter by signup date (end)
            page: Page number (1-indexed)
            page_size: Results per page
            sort: Sort field (created_at, email, last_active_at)
            order: Sort order (asc, desc)

        Returns:
            Dict with items, pagination info, and total count
        """
        try:
            # Build base query
            stmt = select(User).distinct()

            # Apply filters
            conditions = []

            if search:
                search_term = f"%{search}%"
                conditions.append(
                    or_(
                        User.email.ilike(search_term),
                        User.name.ilike(search_term),
                    )
                )

            if plan:
                # Join with subscription
                stmt = stmt.join(
                    Subscription,
                    Subscription.user_id == User.id,
                    isouter=True,
                )
                conditions.append(Subscription.plan == plan)

            if status:
                conditions.append(User.status == status)

            if start_date:
                conditions.append(User.created_at >= start_date)

            if end_date:
                conditions.append(User.created_at <= end_date)

            # Apply all conditions
            if conditions:
                stmt = stmt.where(and_(*conditions))

            # Get total count before pagination
            count_stmt = select(func.count(User.id)).select_from(stmt.froms)
            if conditions:
                count_stmt = count_stmt.where(and_(*conditions))
            total = await db.scalar(count_stmt) or 0

            # Apply sorting
            sort_map = {
                "created_at": User.created_at,
                "email": User.email,
                "last_active_at": User.created_at,  # Simplified
            }
            sort_field = sort_map.get(sort, User.created_at)

            if order == "asc":
                stmt = stmt.order_by(sort_field.asc())
            else:
                stmt = stmt.order_by(sort_field.desc())

            # Apply pagination
            offset = (page - 1) * page_size
            stmt = stmt.offset(offset).limit(page_size)

            results = await db.execute(stmt)
            users = results.scalars().all()

            # Build response items
            items = []
            usage_meter = UsageMeterService()

            for user in users:
                # Get subscription
                sub = await db.scalar(
                    select(Subscription).where(Subscription.user_id == user.id)
                )

                # Get today's usage
                try:
                    usage_today = usage_meter.get_usage(user.id)
                except Exception:
                    usage_today = 0

                # Get last active (simplified)
                last_msg = await db.scalar(
                    select(Message.created_at)
                    .where(Message.user_id == user.id)
                    .order_by(Message.created_at.desc())
                    .limit(1)
                )

                items.append({
                    "id": user.id,
                    "email": user.email,
                    "name": user.name,
                    "plan": sub.plan.value if sub else "free",
                    "status": user.status.value,
                    "messages_used_today": usage_today,
                    "joined_at": user.created_at,
                    "last_active_at": last_msg,
                    "role": user.role.value,
                })

            return {
                "items": items,
                "page": page,
                "page_size": page_size,
                "total": total,
            }

        except Exception as e:
            logger.error(f"Failed to search users: {e}")
            return {"items": [], "page": page, "page_size": page_size, "total": 0}

    @staticmethod
    async def get_user_details(
        db: AsyncSession,
        user_id: UUID,
    ) -> dict:
        """
        Get complete user details including subscription, usage, and activity.

        Args:
            db: Database session
            user_id: User ID to get details for

        Returns:
            Dict with user details
        """
        try:
            # Get user
            user = await db.get(User, user_id)
            if not user:
                return {}

            # Get subscription
            sub = await db.scalar(
                select(Subscription).where(Subscription.user_id == user_id)
            )

            # Get usage
            usage_meter = UsageMeterService()
            try:
                messages_today = usage_meter.get_usage(user_id)
            except Exception:
                messages_today = 0

            # Messages this month
            month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            messages_month = await db.scalar(
                select(func.count(Message.id)).where(
                    (Message.user_id == user_id)
                    & (Message.created_at >= month_start)
                )
            ) or 0

            # Token usage (from model logs if available)
            tokens_used = 0  # Simplified

            # Estimated cost
            estimated_cost = 0.0  # Simplified

            # Recent conversations
            recent_convs = await db.scalar(
                select(func.count(Conversation.id)).where(
                    Conversation.user_id == user_id
                )
            ) or 0

            # Recent messages
            recent_msgs = await db.scalar(
                select(func.count(Message.id)).where(
                    Message.user_id == user_id
                )
            ) or 0

            # Last active
            last_active = await db.scalar(
                select(Message.created_at)
                .where(Message.user_id == user_id)
                .order_by(Message.created_at.desc())
                .limit(1)
            )

            return {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "role": user.role.value,
                "status": user.status.value,
                "is_verified": user.is_verified,
                "joined_at": user.created_at,
                "last_active_at": last_active,
                "plan": sub.plan.value if sub else "free",
                "subscription_status": sub.status.value if sub else None,
                "renewal_date": sub.current_period_end if sub else None,
                "stripe_customer_id": sub.stripe_customer_id if sub else None,
                "cancel_at_period_end": sub.cancel_at_period_end if sub else False,
                "messages_today": messages_today,
                "messages_this_month": messages_month,
                "tokens_used": tokens_used,
                "estimated_cost": estimated_cost,
                "agent_runs": 0,
                "rag_queries": 0,
                "recent_conversations": recent_convs,
                "recent_messages": recent_msgs,
            }

        except Exception as e:
            logger.error(f"Failed to get user details: {e}")
            return {}

    @staticmethod
    async def suspend_user(
        db: AsyncSession,
        user_id: UUID,
        reason: str,
    ) -> dict:
        """
        Suspend a user account.

        Args:
            db: Database session
            user_id: User ID to suspend
            reason: Reason for suspension

        Returns:
            Dict with success status
        """
        try:
            user = await db.get(User, user_id)
            if not user:
                return {"success": False, "message": "User not found"}

            if user.status == UserStatus.suspended:
                return {"success": False, "message": "User already suspended"}

            user.status = UserStatus.suspended
            await db.commit()

            logger.info(f"Suspended user {user_id}: {reason}")

            return {
                "success": True,
                "status": "suspended",
                "message": f"User {user.email} has been suspended",
            }

        except Exception as e:
            logger.error(f"Failed to suspend user: {e}")
            return {"success": False, "message": "Failed to suspend user"}

    @staticmethod
    async def unsuspend_user(
        db: AsyncSession,
        user_id: UUID,
    ) -> dict:
        """
        Unsuspend a user account.

        Args:
            db: Database session
            user_id: User ID to unsuspend

        Returns:
            Dict with success status
        """
        try:
            user = await db.get(User, user_id)
            if not user:
                return {"success": False, "message": "User not found"}

            if user.status != UserStatus.suspended:
                return {"success": False, "message": "User is not suspended"}

            user.status = UserStatus.active
            await db.commit()

            logger.info(f"Unsuspended user {user_id}")

            return {
                "success": True,
                "status": "active",
                "message": f"User {user.email} has been unsuspended",
            }

        except Exception as e:
            logger.error(f"Failed to unsuspend user: {e}")
            return {"success": False, "message": "Failed to unsuspend user"}

    @staticmethod
    async def ban_user(
        db: AsyncSession,
        user_id: UUID,
        reason: str,
    ) -> dict:
        """
        Ban a user account permanently.

        Args:
            db: Database session
            user_id: User ID to ban
            reason: Reason for ban

        Returns:
            Dict with success status
        """
        try:
            user = await db.get(User, user_id)
            if not user:
                return {"success": False, "message": "User not found"}

            if user.status == UserStatus.banned:
                return {"success": False, "message": "User already banned"}

            user.status = UserStatus.banned
            user.is_active = False  # Also disable for belt-and-suspenders
            await db.commit()

            logger.info(f"Banned user {user_id}: {reason}")

            return {
                "success": True,
                "status": "banned",
                "message": f"User {user.email} has been permanently banned",
            }

        except Exception as e:
            logger.error(f"Failed to ban user: {e}")
            return {"success": False, "message": "Failed to ban user"}
