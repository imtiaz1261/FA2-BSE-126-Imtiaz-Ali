"""
Sentry SDK initialization and configuration for error tracking and monitoring.

Captures:
- Unhandled exceptions
- Request context and breadcrumbs
- Performance metrics
- User feedback

Filters sensitive data before sending to Sentry.
"""

import logging
from typing import Optional

import sentry_sdk
from sentry_sdk.integrations.asyncio import AsyncioIntegration
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

from app.config import settings

logger = logging.getLogger(__name__)


class SensitiveDataFilter:
    """Filter for removing sensitive data from Sentry events."""

    SENSITIVE_KEYS = {
        "password",
        "token",
        "secret",
        "key",
        "auth",
        "api_key",
        "private_key",
        "access_token",
        "refresh_token",
        "jwt",
        "authorization",
        "x-api-key",
        "x-auth-token",
        "stripe_key",
        "openai_key",
        "credit_card",
        "ssn",
    }

    @staticmethod
    def before_send(event, hint):
        """Filter sensitive data from Sentry event."""
        # Filter request data
        if "request" in event:
            SensitiveDataFilter._filter_dict(event["request"])

        # Filter exception data
        if "exception" in event:
            for exc in event.get("exception", {}).get("values", []):
                if "stacktrace" in exc:
                    for frame in exc["stacktrace"].get("frames", []):
                        SensitiveDataFilter._filter_dict(frame.get("vars", {}))

        # Filter breadcrumbs
        for breadcrumb in event.get("breadcrumbs", []):
            SensitiveDataFilter._filter_dict(breadcrumb.get("data", {}))

        return event

    @staticmethod
    def _filter_dict(data: dict):
        """Recursively filter sensitive keys from a dictionary."""
        if not isinstance(data, dict):
            return

        for key in list(data.keys()):
            key_lower = key.lower()

            # Check if key is sensitive
            if any(
                sensitive in key_lower
                for sensitive in SensitiveDataFilter.SENSITIVE_KEYS
            ):
                data[key] = "[REDACTED]"
            elif isinstance(data[key], dict):
                SensitiveDataFilter._filter_dict(data[key])
            elif isinstance(data[key], (list, tuple)):
                for item in data[key]:
                    if isinstance(item, dict):
                        SensitiveDataFilter._filter_dict(item)


def init_sentry():
    """Initialize Sentry SDK."""
    if not settings.sentry_dsn:
        logger.info("Sentry DSN not configured, skipping Sentry initialization")
        return

    logger.info(f"Initializing Sentry (environment: {settings.sentry_environment})")

    try:
        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.sentry_environment,
            release=settings.app_version if hasattr(settings, "app_version") else None,
            
            # Integrations
            integrations=[
                FastApiIntegration(),
                AsyncioIntegration(),
                SqlalchemyIntegration(),
                RedisIntegration(),
                LoggingIntegration(
                    level=logging.INFO,  # Capture info and above
                    event_level=logging.ERROR,  # Send error and above as events
                ),
            ],
            
            # Performance Monitoring
            traces_sample_rate=float(settings.sentry_traces_sample_rate or 0.1),
            profiles_sample_rate=float(settings.sentry_profiles_sample_rate or 0.1),
            
            # Error filtering
            before_send=SensitiveDataFilter.before_send,
            
            # Ignore certain errors
            ignore_errors=[
                "HTTPException",  # FastAPI HTTP errors are expected
                "RateLimitExceeded",  # Rate limiting is expected behavior
            ],
            
            # Server options
            send_default_pii=False,  # Don't send PII by default
            attach_stacktrace=True,
            with_local_variables=True,
            
            # Cleanup behavior
            shutdown_timeout=5,
        )

        logger.info("Sentry initialized successfully")

    except Exception as e:
        logger.error(f"Failed to initialize Sentry: {e}")


def capture_exception(
    exception: Exception,
    level: str = "error",
    user_id: Optional[str] = None,
    **extra_context,
):
    """
    Capture an exception to Sentry.

    Args:
        exception: The exception to capture
        level: Error level (debug, info, warning, error, fatal)
        user_id: User ID for context
        **extra_context: Additional context data
    """
    if not settings.sentry_dsn:
        return

    with sentry_sdk.push_scope() as scope:
        if user_id:
            scope.set_user({"id": user_id})

        for key, value in extra_context.items():
            scope.set_context(key, value)

        sentry_sdk.capture_exception(exception, level=level)


def capture_message(
    message: str,
    level: str = "info",
    user_id: Optional[str] = None,
    **extra_context,
):
    """
    Capture a message to Sentry.

    Args:
        message: Message to capture
        level: Message level (debug, info, warning, error, fatal)
        user_id: User ID for context
        **extra_context: Additional context data
    """
    if not settings.sentry_dsn:
        return

    with sentry_sdk.push_scope() as scope:
        if user_id:
            scope.set_user({"id": user_id})

        for key, value in extra_context.items():
            scope.set_context(key, value)

        sentry_sdk.capture_message(message, level=level)


def set_user_context(user_id: str, email: Optional[str] = None, **extra):
    """Set user context for Sentry events."""
    if not settings.sentry_dsn:
        return

    user_data = {"id": user_id}
    if email:
        user_data["email"] = email

    user_data.update(extra)
    sentry_sdk.set_user(user_data)


def clear_user_context():
    """Clear user context from Sentry."""
    if not settings.sentry_dsn:
        return

    sentry_sdk.set_user(None)
