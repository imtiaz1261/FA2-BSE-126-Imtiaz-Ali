"""
Subscription management service.
Handles subscription state, plan management, and synchronization with Stripe.
"""

import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models_billing import Subscription, SubscriptionPlan, SubscriptionStatus
from app.services.stripe_service import StripeService

logger = logging.getLogger(__name__)


class SubscriptionService:
    """Service for subscription management."""

    @staticmethod
    async def get_or_create_subscription(user_id: UUID, db: AsyncSession) -> Subscription:
        """
        Get or create a subscription for a user.

        If user doesn't have a subscription, create a free one.

        Args:
            user_id: User ID
            db: Database session

        Returns:
            Subscription object
        """
        # Try to get existing subscription
        subscription = await db.scalar(
            select(Subscription).where(Subscription.user_id == user_id)
        )

        # If not found, create free subscription
        if not subscription:
            subscription = Subscription(
                user_id=user_id,
                plan=SubscriptionPlan.free,
                status=SubscriptionStatus.active,
            )
            db.add(subscription)
            await db.commit()
            await db.refresh(subscription)
            logger.info(f"Created free subscription for user {user_id}")

        return subscription

    @staticmethod
    async def get_subscription(user_id: UUID, db: AsyncSession) -> Subscription | None:
        """
        Get user's subscription.

        Args:
            user_id: User ID
            db: Database session

        Returns:
            Subscription object or None
        """
        return await db.scalar(
            select(Subscription).where(Subscription.user_id == user_id)
        )

    @staticmethod
    async def create_paid_subscription(
        user_id: UUID,
        stripe_customer_id: str,
        stripe_subscription_id: str,
        stripe_price_id: str,
        plan: str,
        status: str,
        current_period_start: datetime,
        current_period_end: datetime,
        db: AsyncSession,
    ) -> Subscription:
        """
        Create or update a paid subscription.

        Args:
            user_id: User ID
            stripe_customer_id: Stripe customer ID
            stripe_subscription_id: Stripe subscription ID
            stripe_price_id: Stripe price ID
            plan: Plan name (plus or pro)
            status: Stripe subscription status
            current_period_start: Start of billing period
            current_period_end: End of billing period
            db: Database session

        Returns:
            Updated subscription object
        """
        subscription = await db.scalar(
            select(Subscription).where(Subscription.user_id == user_id)
        )

        if not subscription:
            subscription = Subscription(user_id=user_id)
            db.add(subscription)

        # Update subscription
        subscription.stripe_customer_id = stripe_customer_id
        subscription.stripe_subscription_id = stripe_subscription_id
        subscription.stripe_price_id = stripe_price_id
        subscription.plan = SubscriptionPlan(plan)
        subscription.status = SubscriptionStatus(status)
        subscription.current_period_start = current_period_start
        subscription.current_period_end = current_period_end
        subscription.cancel_at_period_end = False

        await db.commit()
        await db.refresh(subscription)

        logger.info(
            f"Updated subscription for user {user_id}: plan={plan}, status={status}"
        )

        return subscription

    @staticmethod
    async def update_subscription_from_stripe(
        stripe_subscription_id: str,
        user_id: UUID,
        db: AsyncSession,
    ) -> Subscription | None:
        """
        Update subscription from Stripe subscription object.

        Args:
            stripe_subscription_id: Stripe subscription ID
            user_id: User ID
            db: Database session

        Returns:
            Updated subscription or None if user not found
        """
        try:
            # Get Stripe subscription
            stripe_sub = StripeService.get_subscription(stripe_subscription_id)

            # Get or create local subscription
            subscription = await SubscriptionService.get_or_create_subscription(user_id, db)

            # Determine plan from price ID
            plan = SubscriptionService._get_plan_from_price_id(stripe_sub.items.data[0].price.id)

            # Update subscription
            subscription.stripe_customer_id = stripe_sub.customer
            subscription.stripe_subscription_id = stripe_sub.id
            subscription.stripe_price_id = stripe_sub.items.data[0].price.id
            subscription.plan = SubscriptionPlan(plan)
            subscription.status = SubscriptionStatus(stripe_sub.status)
            subscription.current_period_start = datetime.fromtimestamp(
                stripe_sub.current_period_start, tz=datetime.now().astimezone().tzinfo
            )
            subscription.current_period_end = datetime.fromtimestamp(
                stripe_sub.current_period_end, tz=datetime.now().astimezone().tzinfo
            )
            subscription.cancel_at_period_end = stripe_sub.cancel_at_period_end

            await db.commit()
            await db.refresh(subscription)

            logger.info(
                f"Synced subscription for user {user_id} from Stripe: plan={plan}"
            )

            return subscription

        except Exception as e:
            logger.error(f"Failed to sync subscription: {e}")
            return None

    @staticmethod
    async def downgrade_to_free(user_id: UUID, db: AsyncSession) -> Subscription:
        """
        Downgrade user to free plan.

        Called when subscription is deleted or canceled.

        Args:
            user_id: User ID
            db: Database session

        Returns:
            Updated subscription
        """
        subscription = await SubscriptionService.get_or_create_subscription(user_id, db)

        subscription.plan = SubscriptionPlan.free
        subscription.status = SubscriptionStatus.active
        subscription.stripe_customer_id = None
        subscription.stripe_subscription_id = None
        subscription.stripe_price_id = None
        subscription.current_period_start = None
        subscription.current_period_end = None
        subscription.cancel_at_period_end = False

        await db.commit()
        await db.refresh(subscription)

        logger.info(f"Downgraded user {user_id} to free plan")

        return subscription

    @staticmethod
    def _get_plan_from_price_id(price_id: str) -> str:
        """
        Determine plan from Stripe price ID.

        Args:
            price_id: Stripe price ID

        Returns:
            Plan name (plus or pro)
        """
        from app.config_billing import billing_config

        if price_id == billing_config.stripe_plus_price_id:
            return "plus"
        elif price_id == billing_config.stripe_pro_price_id:
            return "pro"
        else:
            logger.warning(f"Unknown price ID: {price_id}, defaulting to plus")
            return "plus"

    @staticmethod
    async def update_subscription_status(
        user_id: UUID,
        new_status: str,
        db: AsyncSession,
    ) -> Subscription | None:
        """
        Update subscription status (e.g., past_due, canceled, etc.).

        Args:
            user_id: User ID
            new_status: New Stripe status
            db: Database session

        Returns:
            Updated subscription or None
        """
        subscription = await SubscriptionService.get_subscription(user_id, db)

        if not subscription:
            return None

        subscription.status = SubscriptionStatus(new_status)

        await db.commit()
        await db.refresh(subscription)

        logger.info(f"Updated subscription status for user {user_id}: {new_status}")

        return subscription

    @staticmethod
    async def is_active_subscription(subscription: Subscription) -> bool:
        """
        Check if subscription is active and not past_due or canceled.

        Args:
            subscription: Subscription object

        Returns:
            True if active
        """
        active_statuses = [
            SubscriptionStatus.active,
            SubscriptionStatus.trialing,
        ]
        return subscription.status in active_statuses
