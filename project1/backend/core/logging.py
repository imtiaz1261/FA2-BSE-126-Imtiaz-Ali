"""
core/logging.py — Structured Application Logging
=================================================
Configures structlog for structured JSON logging in production
and human-readable coloured output in development.

Compatible with structlog >= 21.x (tested on 24.x and 26.x).
"""

import logging
import sys
from typing import Any

import structlog
from backend.core.config import settings


def configure_logging() -> None:
    """
    Call once at application startup (in main.py lifespan).
    Sets up both the standard library logging and structlog processors.
    """
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    # Shared processors — applied to every log entry
    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if settings.LOG_FORMAT == "json":
        # Production: machine-readable JSON
        processors = shared_processors + [
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ]
    else:
        # Development: human-readable (no colours to avoid Windows issues)
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=False),
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Route standard library logging through structlog
    logging.basicConfig(
        format="%(levelname)s %(name)s %(message)s",
        stream=sys.stdout,
        level=log_level,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Return a named bound logger.

    Args:
        name: Typically __name__ of the calling module.

    Returns:
        A structlog BoundLogger instance.
    """
    return structlog.get_logger(name)
