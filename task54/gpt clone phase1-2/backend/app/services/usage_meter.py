"""
Redis-based usage metering service.
Handles daily message counters and quota enforcement.
"""

import logging
from datetime import datetime, timedelta
from uuid import UUID

import redis

from app.config_billing import billing_config, get_billing_config

logger = logging.getLogger(__name__)


class UsageMeterService:
    """Service for usage metering and quota management."""

    def __init__(self, redis_url: str | None = None):
        """
        Initialize usage meter service.

        Args:
            redis_url: Redis connection URL (uses env var if not provided)
        """
        url = redis_url or billing_config.redis_url
        try:
            self.redis = redis.from_url(url, decode_responses=True)
            # Test connection
            self.redis.ping()
            logger.info(f"Connected to Redis: {url}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    def _get_usage_key(self, user_id: UUID) -> str:
        """
        Get Redis key for today's usage.

        Args:
            user_id: User ID

        Returns:
            Redis key
        """
        today = datetime.utcnow().strftime("%Y-%m-%d")
        return f"usage:user:{user_id}:{today}"

    def get_usage(self, user_id: UUID) -> int:
        """
        Get current daily usage for user.

        Args:
            user_id: User ID

        Returns:
            Number of messages used today
        """
        try:
            key = self._get_usage_key(user_id)
            usage = self.redis.get(key)
            return int(usage) if usage else 0
        except Exception as e:
            logger.error(f"Failed to get usage for user {user_id}: {e}")
            return 0

    def increment_usage(self, user_id: UUID, amount: int = 1) -> int:
        """
        Increment usage counter atomically.

        Args:
            user_id: User ID
            amount: Amount to increment (default 1)

        Returns:
            New usage count

        Raises:
            RuntimeError: If Redis operation fails
        """
        try:
            key = self._get_usage_key(user_id)

            # Increment atomically
            new_count = self.redis.incr(key, amount)

            # Set TTL to midnight UTC (prevent key bloat)
            ttl_seconds = self._get_ttl_to_midnight()
            self.redis.expire(key, ttl_seconds)

            logger.debug(f"Incremented usage for user {user_id}: {new_count}")

            return new_count

        except Exception as e:
            logger.error(f"Failed to increment usage for user {user_id}: {e}")
            raise RuntimeError(f"Usage meter error: {e}")

    def check_limit(self, user_id: UUID, plan: str) -> tuple[bool, int, int]:
        """
        Check if user has exceeded daily limit.

        Args:
            user_id: User ID
            plan: Subscription plan (free, plus, pro)

        Returns:
            Tuple of (under_limit, used, limit)
        """
        config = get_billing_config()
        limit = config.get_daily_limit(plan)
        used = self.get_usage(user_id)

        under_limit = used < limit

        return under_limit, used, limit

    def get_remaining_usage(self, user_id: UUID, plan: str) -> int:
        """
        Get remaining daily messages for user.

        Args:
            user_id: User ID
            plan: Subscription plan

        Returns:
            Number of messages remaining (0 if limit reached)
        """
        config = get_billing_config()
        limit = config.get_daily_limit(plan)
        used = self.get_usage(user_id)

        remaining = max(0, limit - used)

        return remaining

    def get_usage_percentage(self, user_id: UUID, plan: str) -> int:
        """
        Get usage as percentage of daily limit.

        Args:
            user_id: User ID
            plan: Subscription plan

        Returns:
            Percentage (0-100)
        """
        config = get_billing_config()
        limit = config.get_daily_limit(plan)

        if limit == 0:
            return 0

        used = self.get_usage(user_id)
        percentage = int((used / limit) * 100)

        return min(100, percentage)

    def get_reset_time(self) -> datetime:
        """
        Get time when daily limit resets (UTC midnight).

        Returns:
            Datetime of next midnight UTC
        """
        now = datetime.utcnow()
        tomorrow_midnight = (now + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        return tomorrow_midnight

    def reset_usage_if_required(self, user_id: UUID) -> bool:
        """
        Check if usage key has expired and reset if needed.

        In practice, Redis TTL handles this automatically, but this
        provides an explicit way to check/reset.

        Args:
            user_id: User ID

        Returns:
            True if usage was reset, False if still valid
        """
        key = self._get_usage_key(user_id)
        ttl = self.redis.ttl(key)

        # TTL of -1 means key exists with no expiry (shouldn't happen)
        # TTL of -2 means key doesn't exist (already reset)
        if ttl == -2:
            logger.debug(f"Usage for user {user_id} already reset (key expired)")
            return True

        return False

    def _get_ttl_to_midnight(self) -> int:
        """
        Get seconds until midnight UTC.

        Returns:
            Seconds until midnight
        """
        now = datetime.utcnow()
        tomorrow_midnight = (now + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        ttl = int((tomorrow_midnight - now).total_seconds())
        return max(1, ttl)  # Ensure at least 1 second

    def health_check(self) -> bool:
        """
        Check Redis connection health.

        Returns:
            True if Redis is accessible
        """
        try:
            self.redis.ping()
            return True
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False

    def clear_user_usage(self, user_id: UUID) -> bool:
        """
        Clear usage for user (admin function).

        Args:
            user_id: User ID

        Returns:
            True if cleared
        """
        try:
            key = self._get_usage_key(user_id)
            deleted = self.redis.delete(key)
            logger.info(f"Cleared usage for user {user_id}")
            return deleted > 0
        except Exception as e:
            logger.error(f"Failed to clear usage for user {user_id}: {e}")
            return False


# Singleton instance
_usage_meter = None


def get_usage_meter() -> UsageMeterService:
    """Get singleton usage meter instance."""
    global _usage_meter
    if _usage_meter is None:
        _usage_meter = UsageMeterService()
    return _usage_meter
