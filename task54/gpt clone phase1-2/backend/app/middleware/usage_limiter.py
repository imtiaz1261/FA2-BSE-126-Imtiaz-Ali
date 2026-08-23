"""
Usage Limiter Middleware & FastAPI Dependency

Enforces plan-based daily message quotas before LLM calls.
Prevents users from exceeding their subscription limits.
"""

import logging
from typing import Optional

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config_billing import billing_config
from app.dependencies import get_current_user, get_db
from app.models import User
from app.models_billing import SubscriptionPlan
from app.services.subscription_service import SubscriptionService
from app.services.usage_meter import UsageMeterService

logger = logging.getLogger(__name__)

subscription_service = SubscriptionService()
usage_meter = UsageMeterService()


class UsageLimitError(Exception):
    """Raised when user has exceeded quota."""

    def __init__(self, message: str, reset_at: str, remaining: int = 0):
        self.message = message
        self.reset_at = reset_at
        self.remaining = remaining
        super().__init__(message)


async def enforce_usage_limit(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    FastAPI dependency that enforces daily message quota.

    Call this in chat endpoints (POST /chat/stream) to block requests
    if user has exceeded their daily limit.

    Args:
        current_user: Authenticated user
        db: Database session

    Returns:
        Dict with usage info: {daily_limit, used_today, remaining, reset_at}

    Raises:
        HTTPException (429): If daily limit exceeded

    Usage:
        @router.post("/stream")
        async def chat_stream(
            ...,
            usage_info = Depends(enforce_usage_limit),
        ):
            ...
    """
    try:
        user_id = str(current_user.id)

        # Get user's subscription
        subscription = await subscription_service.get_or_create_subscription(
            user_id, db
        )

        # Get daily limit for their plan
        daily_limit = billing_config.get_daily_limit(subscription.plan.value)

        # Get current usage
        usage_count = await usage_meter.get_daily_usage(user_id)

        # Check if over limit
        if usage_count >= daily_limit:
            reset_time = usage_meter.get_reset_time()
            logger.warning(
                f"User {user_id} exceeded daily limit ({usage_count}/{daily_limit})"
            )

            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "message": f"Daily message limit ({daily_limit}) exceeded",
                    "plan": subscription.plan.value,
                    "daily_limit": daily_limit,
                    "used_today": usage_count,
                    "remaining": 0,
                    "reset_at": reset_time,
                    "error_code": "QUOTA_EXCEEDED",
                },
                headers={"Retry-After": "86400"},  # 24 hours
            )

        # Return usage info
        return {
            "daily_limit": daily_limit,
            "used_today": usage_count,
            "remaining": daily_limit - usage_count,
            "reset_at": usage_meter.get_reset_time(),
            "plan": subscription.plan.value,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Usage limit check failed: {e}", exc_info=True)
        # On error, don't block; let request through
        return {
            "daily_limit": -1,
            "used_today": -1,
            "remaining": -1,
            "reset_at": usage_meter.get_reset_time(),
            "plan": "unknown",
        }


async def increment_usage(
    current_user: User,
    db: AsyncSession,
    count: int = 1,
) -> int:
    """
    Increment usage counter after successful LLM call.

    Should be called AFTER the LLM response is complete, not before.
    This ensures we only count successful generations.

    Args:
        current_user: Authenticated user
        db: Database session
        count: Number of messages to add (default 1)

    Returns:
        New total usage count for today
    """
    try:
        user_id = str(current_user.id)
        new_count = await usage_meter.increment_daily_usage(user_id, count)

        logger.debug(f"Incremented usage for user {user_id}: +{count} (total: {new_count})")

        return new_count

    except Exception as e:
        logger.error(f"Failed to increment usage: {e}")
        # Don't raise; usage tracking failure shouldn't break the chat
        return -1


async def get_usage_info(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get current usage information without enforcing quota.

    Useful for UI display, not for quota enforcement.

    Args:
        current_user: Authenticated user
        db: Database session

    Returns:
        Dict with usage stats
    """
    try:
        user_id = str(current_user.id)

        # Get subscription
        subscription = await subscription_service.get_or_create_subscription(
            user_id, db
        )

        # Get limit and usage
        daily_limit = billing_config.get_daily_limit(subscription.plan.value)
        usage_count = await usage_meter.get_daily_usage(user_id)

        return {
            "plan": subscription.plan.value,
            "daily_limit": daily_limit,
            "used_today": usage_count,
            "remaining": max(0, daily_limit - usage_count),
            "percentage_used": (usage_count / daily_limit * 100)
            if daily_limit > 0
            else 0,
            "reset_at": usage_meter.get_reset_time(),
            "status": (
                "exceeded"
                if usage_count >= daily_limit
                else "warning" if usage_count >= daily_limit * 0.8 else "ok"
            ),
        }

    except Exception as e:
        logger.error(f"Failed to get usage info: {e}")
        return {
            "plan": "unknown",
            "daily_limit": -1,
            "used_today": -1,
            "remaining": -1,
            "percentage_used": -1,
            "reset_at": usage_meter.get_reset_time(),
            "status": "unknown",
        }


class UsageLimiterMiddleware:
    """
    ASGI middleware for usage rate limiting (alternative to dependency).

    Not recommended for production since it applies globally.
    Use the dependency approach instead to limit only chat endpoints.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        """Apply middleware."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Check if this is a chat endpoint
        path = scope.get("path", "")
        if not path.startswith("/api/chat/stream"):
            await self.app(scope, receive, send)
            return

        # Would need to extract user from request here
        # For now, just pass through (use dependency in route instead)
        await self.app(scope, receive, send)
