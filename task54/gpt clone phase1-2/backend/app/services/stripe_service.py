"""
Stripe API integration service.
Handles customer creation, subscription management, checkout, and portal sessions.
"""

import logging
from typing import Optional

import stripe

from app.config_billing import billing_config

logger = logging.getLogger(__name__)

# Configure Stripe
stripe.api_key = billing_config.stripe_secret_key


class StripeService:
    """Service for Stripe operations."""

    @staticmethod
    def create_customer(email: str, name: str | None = None, user_id: str | None = None) -> str:
        """
        Create a Stripe customer.

        Args:
            email: Customer email
            name: Customer name (optional)
            user_id: Internal user ID for metadata

        Returns:
            Stripe customer ID

        Raises:
            stripe.error.StripeError: If creation fails
        """
        try:
            metadata = {}
            if user_id:
                metadata["user_id"] = str(user_id)

            customer = stripe.Customer.create(
                email=email,
                name=name,
                metadata=metadata,
            )

            logger.info(f"Created Stripe customer {customer.id} for {email}")
            return customer.id

        except stripe.error.StripeError as e:
            logger.error(f"Failed to create Stripe customer: {e}")
            raise

    @staticmethod
    def get_customer(customer_id: str) -> stripe.Customer:
        """
        Get Stripe customer.

        Args:
            customer_id: Stripe customer ID

        Returns:
            Stripe customer object

        Raises:
            stripe.error.InvalidRequestError: If customer not found
        """
        try:
            return stripe.Customer.retrieve(customer_id)
        except stripe.error.InvalidRequestError as e:
            logger.error(f"Customer not found: {customer_id}")
            raise

    @staticmethod
    def create_checkout_session(
        customer_id: str,
        price_id: str,
        success_url: str,
        cancel_url: str,
        user_id: str | None = None,
    ) -> str:
        """
        Create Stripe Checkout Session.

        Args:
            customer_id: Stripe customer ID
            price_id: Stripe price ID (product pricing)
            success_url: Redirect URL after successful payment
            cancel_url: Redirect URL if user cancels
            user_id: Internal user ID for metadata

        Returns:
            Checkout session URL

        Raises:
            stripe.error.StripeError: If creation fails
        """
        try:
            metadata = {}
            if user_id:
                metadata["user_id"] = str(user_id)

            session = stripe.checkout.Session.create(
                customer=customer_id,
                payment_method_types=["card"],
                mode="subscription",
                line_items=[
                    {
                        "price": price_id,
                        "quantity": 1,
                    }
                ],
                success_url=success_url,
                cancel_url=cancel_url,
                metadata=metadata,
            )

            logger.info(f"Created checkout session {session.id} for customer {customer_id}")
            return session.url

        except stripe.error.StripeError as e:
            logger.error(f"Failed to create checkout session: {e}")
            raise

    @staticmethod
    def create_portal_session(customer_id: str, return_url: str) -> str:
        """
        Create Stripe Billing Portal session.

        Args:
            customer_id: Stripe customer ID
            return_url: URL to return to after portal

        Returns:
            Portal session URL

        Raises:
            stripe.error.StripeError: If creation fails
        """
        try:
            session = stripe.billing_portal.Session.create(
                customer=customer_id,
                return_url=return_url,
            )

            logger.info(f"Created portal session for customer {customer_id}")
            return session.url

        except stripe.error.StripeError as e:
            logger.error(f"Failed to create portal session: {e}")
            raise

    @staticmethod
    def get_subscription(subscription_id: str) -> stripe.Subscription:
        """
        Get Stripe subscription.

        Args:
            subscription_id: Stripe subscription ID

        Returns:
            Stripe subscription object

        Raises:
            stripe.error.InvalidRequestError: If subscription not found
        """
        try:
            return stripe.Subscription.retrieve(subscription_id)
        except stripe.error.InvalidRequestError as e:
            logger.error(f"Subscription not found: {subscription_id}")
            raise

    @staticmethod
    def cancel_subscription(
        subscription_id: str,
        at_period_end: bool = True,
    ) -> stripe.Subscription:
        """
        Cancel Stripe subscription.

        Args:
            subscription_id: Stripe subscription ID
            at_period_end: If True, cancel at end of current period. If False, cancel immediately.

        Returns:
            Updated subscription object

        Raises:
            stripe.error.StripeError: If cancellation fails
        """
        try:
            if at_period_end:
                subscription = stripe.Subscription.modify(
                    subscription_id,
                    cancel_at_period_end=True,
                )
                logger.info(f"Subscription {subscription_id} scheduled for cancellation")
            else:
                subscription = stripe.Subscription.delete(subscription_id)
                logger.info(f"Subscription {subscription_id} canceled immediately")

            return subscription

        except stripe.error.StripeError as e:
            logger.error(f"Failed to cancel subscription: {e}")
            raise

    @staticmethod
    def verify_webhook_signature(payload: bytes, sig_header: str) -> dict:
        """
        Verify Stripe webhook signature.

        Args:
            payload: Raw request body
            sig_header: Stripe-Signature header value

        Returns:
            Parsed webhook event

        Raises:
            stripe.error.SignatureVerificationError: If signature invalid
        """
        try:
            event = stripe.Webhook.construct_event(
                payload,
                sig_header,
                billing_config.stripe_webhook_secret,
            )
            logger.info(f"Verified webhook signature: {event['type']}")
            return event

        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Webhook signature verification failed: {e}")
            raise

    @staticmethod
    def get_price(price_id: str) -> stripe.Price:
        """
        Get Stripe price.

        Args:
            price_id: Stripe price ID

        Returns:
            Stripe price object

        Raises:
            stripe.error.InvalidRequestError: If price not found
        """
        try:
            return stripe.Price.retrieve(price_id)
        except stripe.error.InvalidRequestError as e:
            logger.error(f"Price not found: {price_id}")
            raise
