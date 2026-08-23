"""
Structured JSON logging configuration for production.

Provides:
- JSON-formatted logs with structured fields
- Request/correlation ID tracking
- Sensitive data filtering
- Integration with Sentry
"""

import json
import logging
import sys
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.config import settings


class JSONFormatter(logging.Formatter):
    """Custom formatter that outputs structured JSON logs."""

    # Fields that should never be logged (secrets, passwords, tokens)
    SENSITIVE_FIELDS = {
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
    }

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": settings.app_name,
            "environment": settings.environment,
        }

        # Add request ID if available
        request_id = getattr(record, "request_id", None)
        if request_id:
            log_data["request_id"] = request_id

        # Add correlation ID if available
        correlation_id = getattr(record, "correlation_id", None)
        if correlation_id:
            log_data["correlation_id"] = correlation_id

        # Add user ID if available
        user_id = getattr(record, "user_id", None)
        if user_id:
            log_data["user_id"] = user_id

        # Add extra fields
        if hasattr(record, "extra"):
            extra = record.extra
            for key, value in extra.items():
                if not self._is_sensitive(key):
                    log_data[key] = self._sanitize_value(value)

        # Add exception info
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info),
            }

        # Add stack info if available
        if record.stack_info:
            log_data["stack"] = record.stack_info

        return json.dumps(log_data, default=str)

    @staticmethod
    def _is_sensitive(field_name: str) -> bool:
        """Check if a field name should be redacted."""
        field_lower = field_name.lower()
        return any(
            sensitive in field_lower
            for sensitive in JSONFormatter.SENSITIVE_FIELDS
        )

    @staticmethod
    def _sanitize_value(value: Any) -> Any:
        """Sanitize potentially sensitive values."""
        if isinstance(value, str):
            # Redact common secret patterns
            if any(
                pattern in value.lower()
                for pattern in ["sk_", "pk_", "bearer", "token="]
            ):
                return "[REDACTED]"
        return value


class StructuredLogger:
    """Helper class for structured logging with context."""

    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.request_id = str(uuid.uuid4())
        self.correlation_id: Optional[str] = None
        self.user_id: Optional[str] = None

    def set_request_context(
        self,
        request_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ):
        """Set the request context for logging."""
        if request_id:
            self.request_id = request_id
        if correlation_id:
            self.correlation_id = correlation_id
        if user_id:
            self.user_id = user_id

    def _add_context(self, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Add context to log record."""
        context = {"extra": extra or {}}
        if self.request_id:
            context["request_id"] = self.request_id
        if self.correlation_id:
            context["correlation_id"] = self.correlation_id
        if self.user_id:
            context["user_id"] = self.user_id
        return context

    def debug(self, message: str, **kwargs):
        """Log debug message."""
        self.logger.debug(message, extra=self._add_context(kwargs))

    def info(self, message: str, **kwargs):
        """Log info message."""
        self.logger.info(message, extra=self._add_context(kwargs))

    def warning(self, message: str, **kwargs):
        """Log warning message."""
        self.logger.warning(message, extra=self._add_context(kwargs))

    def error(self, message: str, exc_info: bool = False, **kwargs):
        """Log error message."""
        self.logger.error(message, exc_info=exc_info, extra=self._add_context(kwargs))

    def critical(self, message: str, **kwargs):
        """Log critical message."""
        self.logger.critical(message, extra=self._add_context(kwargs))


def setup_logging():
    """Configure structured JSON logging for the application."""
    # Create logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, settings.log_level.upper()))

    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Create console handler with JSON formatter
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(JSONFormatter())

    # Add handler to logger
    logger.addHandler(console_handler)

    # Set logging level for specific noisy loggers
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    return logger


def get_structured_logger(name: str) -> StructuredLogger:
    """Get a structured logger instance."""
    logger = logging.getLogger(name)
    return StructuredLogger(logger)
