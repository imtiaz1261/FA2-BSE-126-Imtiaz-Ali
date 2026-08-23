"""
Billing & pricing configuration.
Centralized place for all plan definitions, limits, and Stripe pricing.
"""

import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass
class Plan:
    """Plan configuration."""
    name: str
    price: int  # cents (e.g., 1999 = $19.99)
    currency: str
    interval: str  # "month" or "year"
    daily_messages: int
    description: str
    features: list[str]
    stripe_price_id: str | None = None  # From environment


class BillingConfig:
    """Billing configuration manager."""

    def __init__(self):
        """Initialize with environment variables and defaults."""
        # Stripe keys
        self.stripe_secret_key = os.getenv("STRIPE_SECRET_KEY", "")
        self.stripe_publishable_key = os.getenv("STRIPE_PUBLISHABLE_KEY", "")
        self.stripe_webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")

        # Daily message limits
        self.free_daily_messages = int(os.getenv("FREE_DAILY_MESSAGES", "20"))
        self.plus_daily_messages = int(os.getenv("PLUS_DAILY_MESSAGES", "300"))
        self.pro_daily_messages = int(os.getenv("PRO_DAILY_MESSAGES", "1000"))

        # Stripe Price IDs (from environment)
        self.stripe_plus_price_id = os.getenv("STRIPE_PLUS_PRICE_ID", "")
        self.stripe_pro_price_id = os.getenv("STRIPE_PRO_PRICE_ID", "")

        # Redis
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    def get_plans(self) -> dict[str, Plan]:
        """Get all subscription plans."""
        return {
            "free": Plan(
                name="Free",
                price=0,
                currency="USD",
                interval="month",
                daily_messages=self.free_daily_messages,
                description="Perfect for getting started",
                features=[
                    f"✓ {self.free_daily_messages} messages/day",
                    "✓ Standard AI model",
                    "✓ Basic chat history",
                    "✓ Limited file uploads",
                    "✓ Basic memory",
                ],
                stripe_price_id=None,
            ),
            "plus": Plan(
                name="Plus",
                price=1999,  # $19.99
                currency="USD",
                interval="month",
                daily_messages=self.plus_daily_messages,
                description="Most popular for active users",
                features=[
                    f"✓ {self.plus_daily_messages} messages/day",
                    "✓ Advanced AI models",
                    "✓ Larger file uploads",
                    "✓ Priority responses",
                    "✓ Extended memory",
                    "✓ Longer chat history",
                ],
                stripe_price_id=self.stripe_plus_price_id,
            ),
            "pro": Plan(
                name="Pro",
                price=4999,  # $49.99
                currency="USD",
                interval="month",
                daily_messages=self.pro_daily_messages,
                description="For power users",
                features=[
                    f"✓ {self.pro_daily_messages} messages/day",
                    "✓ Advanced AI models",
                    "✓ Large file uploads",
                    "✓ Priority processing",
                    "✓ Advanced memory",
                    "✓ Usage analytics",
                    "✓ Priority support",
                ],
                stripe_price_id=self.stripe_pro_price_id,
            ),
        }

    def get_plan(self, plan_name: str) -> Plan | None:
        """Get a specific plan by name."""
        plans = self.get_plans()
        return plans.get(plan_name)

    def get_daily_limit(self, plan_name: str) -> int:
        """Get daily message limit for a plan."""
        plan = self.get_plan(plan_name)
        return plan.daily_messages if plan else 0

    def get_stripe_price_id(self, plan_name: str) -> str | None:
        """Get Stripe price ID for a plan."""
        plan = self.get_plan(plan_name)
        return plan.stripe_price_id if plan else None

    def validate_plan(self, plan_name: str) -> bool:
        """Validate that plan exists."""
        return plan_name in self.get_plans()

    def validate_stripe_config(self) -> tuple[bool, str]:
        """Validate Stripe configuration."""
        if not self.stripe_secret_key:
            return False, "STRIPE_SECRET_KEY not set"
        if not self.stripe_publishable_key:
            return False, "STRIPE_PUBLISHABLE_KEY not set"
        if not self.stripe_webhook_secret:
            return False, "STRIPE_WEBHOOK_SECRET not set"
        if not self.stripe_plus_price_id:
            return False, "STRIPE_PLUS_PRICE_ID not set"
        if not self.stripe_pro_price_id:
            return False, "STRIPE_PRO_PRICE_ID not set"
        return True, "OK"


@lru_cache
def get_billing_config() -> BillingConfig:
    """Get singleton billing configuration."""
    return BillingConfig()


billing_config = get_billing_config()
