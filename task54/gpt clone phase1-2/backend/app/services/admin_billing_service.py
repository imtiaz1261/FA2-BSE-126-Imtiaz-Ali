"""
Admin billing service.

Handles:
- Plan changes
- Refunds
- Stripe subscription management
- Billing operations
"""
import logging
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User
from app.models_billing import Subscription, SubscriptionPlan, SubscriptionStatus
from app.services.stripe_service import StripeService
from app.services.subscription_service import SubscriptionService

logger = logging.getLogger(__name__)


class AdminBillingService:
    """Service for admin billing operations."""

    def __init__(self):
        """Initialize billing service."""
        self.stripe_service = StripeService()
        self.subscription_service = SubscriptionService()

    async def change_user_plan(
        self,
        db: AsyncSession,
        user_id: UUID,
        new_plan: str,
    ) -> dict:
        """
        Change a user's subscription plan.

        For paid plans, synchronizes with Stripe before updating database.
        For free plan, cancels paid subscription appropriately.

        Args:
            db: Database session
            user_id: User ID to change plan for
            new_plan: Target plan (free, plus, pro)

        Returns:
            Dict with success status and new plan
        """
        try:
            # Validate plan
            if new_plan not in ["free", "plus", "pro"]:
                return {"success": False, "message": "Invalid plan"}

            # Get user and current subscription
            user = await db.get(User, user_id)
            if not user:
                return {"success": False, "message": "User not found"}

            subscription = await db.scalar(
                select(Subscription).where(Subscription.user_id == user_id)
            )

            if not subscription:
                return {"success": False, "message": "User subscription not found"}

            current_plan = subscription.plan.value

            # If changing to same plan, no-op
            if current_plan == new_plan:
                return {
                    "success": True,
                    "new_plan": new_plan,
                    "message": f"User already on {new_plan} plan",
                }

            # If downgrading to free, cancel Stripe subscription
            if new_plan == "free" and current_plan in ["plus", "pro"]:
                if subscription.stripe_subscription_id:
                    try:
                        # Cancel at period end to allow usage through current period
                        await self.stripe_service.cancel_subscription(
                            subscription.stripe_subscription_id,
                            cancel_at_period_end=True,
                        )

                        subscription.cancel_at_period_end = True
                        logger.info(
                            f"Cancelled Stripe subscription for user {user_id}"
                        )
                    except Exception as e:
                        logger.error(f"Failed to cancel Stripe subscription: {e}")
                        return {
                            "success": False,
                            "message": "Failed to cancel Stripe subscription",
                        }

                # Downgrade to free in DB
                subscription.plan = SubscriptionPlan.free
                subscription.stripe_subscription_id = None
                subscription.stripe_price_id = None
                await db.commit()

                logger.info(f"Downgraded user {user_id} to free plan")

                return {
                    "success": True,
                    "new_plan": "free",
                    "message": f"User {user.email} downgraded to free plan",
                }

            # If upgrading to paid plan, create/update Stripe subscription
            if new_plan in ["plus", "pro"]:
                try:
                    # Get or create Stripe customer
                    if not subscription.stripe_customer_id:
                        customer = await self.stripe_service.create_customer(
                            user_id=str(user_id),
                            email=user.email,
                        )
                        subscription.stripe_customer_id = customer.id
                    else:
                        customer = await self.stripe_service.get_customer(
                            subscription.stripe_customer_id
                        )

                    # Get price ID for target plan
                    from app.config_billing import billing_config
                    price_id = billing_config.get_stripe_price_id(new_plan)

                    if not price_id:
                        return {
                            "success": False,
                            "message": f"Stripe price ID not configured for {new_plan}",
                        }

                    # Create or update subscription in Stripe
                    if subscription.stripe_subscription_id:
                        # Update existing subscription
                        stripe_sub = await self.stripe_service.update_subscription(
                            subscription.stripe_subscription_id,
                            price_id=price_id,
                        )
                    else:
                        # Create new subscription
                        stripe_sub = await self.stripe_service.create_subscription(
                            customer_id=subscription.stripe_customer_id,
                            price_id=price_id,
                        )

                    # Update local subscription from Stripe
                    subscription.stripe_subscription_id = stripe_sub.id
                    subscription.stripe_price_id = price_id
                    subscription.plan = SubscriptionPlan(new_plan)
                    subscription.status = SubscriptionStatus(stripe_sub.status)
                    subscription.cancel_at_period_end = False

                    await db.commit()

                    logger.info(f"Upgraded user {user_id} to {new_plan} plan")

                    return {
                        "success": True,
                        "new_plan": new_plan,
                        "message": f"User {user.email} upgraded to {new_plan} plan",
                    }

                except Exception as e:
                    logger.error(f"Failed to create Stripe subscription: {e}")
                    return {
                        "success": False,
                        "message": "Failed to update Stripe subscription",
                    }

            return {"success": False, "message": "Plan change not allowed"}

        except Exception as e:
            logger.error(f"Failed to change user plan: {e}")
            return {"success": False, "message": "Failed to change plan"}

    async def issue_refund(
        self,
        db: AsyncSession,
        user_id: UUID,
        payment_intent_id: str,
        amount: Optional[float] = None,
        reason: str = "",
    ) -> dict:
        """
        Issue a refund for a payment.

        Supports both full and partial refunds via Stripe.

        Args:
            db: Database session
            user_id: User ID to refund
            payment_intent_id: Stripe payment intent ID
            amount: Amount to refund (None for full refund)
            reason: Reason for refund

        Returns:
            Dict with refund details
        """
        try:
            # Verify user exists
            user = await db.get(User, user_id)
            if not user:
                return {"success": False, "message": "User not found"}

            # Process refund via Stripe
            try:
                refund = await self.stripe_service.create_refund(
                    payment_intent_id=payment_intent_id,
                    amount=int(amount * 100) if amount else None,  # Convert to cents
                    reason=reason,
                )

                logger.info(
                    f"Issued refund {refund.id} for user {user_id}: {reason}"
                )

                return {
                    "success": True,
                    "refund_id": refund.id,
                    "status": refund.status,
                    "amount": refund.amount / 100,  # Convert back to dollars
                    "message": f"Refund processed: {refund.id}",
                }

            except Exception as e:
                logger.error(f"Stripe refund failed: {e}")
                return {
                    "success": False,
                    "message": f"Stripe refund failed: {str(e)}",
                }

        except Exception as e:
            logger.error(f"Failed to issue refund: {e}")
            return {"success": False, "message": "Failed to issue refund"}
