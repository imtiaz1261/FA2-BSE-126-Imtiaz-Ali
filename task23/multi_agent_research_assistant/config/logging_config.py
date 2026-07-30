"""
Logging configuration for AI Research Assistant.

Supports two modes controlled by settings.log_format:
  - "console"  →  Rich-formatted, human-readable output (development)
  - "json"     →  Structured JSON output (production / log aggregators)

Usage:
    from config.logging_config import setup_logging, get_logger

    setup_logging()                    # call once at app startup
    logger = get_logger(__name__)      # in each module
    logger.info("agent_started", agent="researcher", query="LangGraph intro")
"""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog
from rich.console import Console
from rich.logging import RichHandler

# Shared Rich console (can be reused in other modules for pretty printing)
console = Console()


def setup_logging(log_level: str = "INFO", log_format: str = "console") -> None:
    """
    Initialise the logging stack.

    Sets up:
    - Python's stdlib logging with the appropriate handler
    - structlog processors for structured, context-rich log events

    Args:
        log_level:  Minimum level to emit (DEBUG / INFO / WARNING / ERROR / CRITICAL).
        log_format: "console" for Rich pretty output, "json" for machine-readable.
    """
    level = getattr(logging, log_level.upper(), logging.INFO)

    # ── 1. Configure stdlib logging handler ───────────────────────────────────
    if log_format == "console":
        handler: logging.Handler = RichHandler(
            console=console,
            show_time=True,
            show_path=True,
            rich_tracebacks=True,
            tracebacks_show_locals=False,
            markup=True,
        )
        handler.setFormatter(logging.Formatter("%(message)s"))
    else:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("%(message)s"))

    # Root logger — affects all libraries too
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    # Remove existing handlers to prevent duplicate output
    root_logger.handlers.clear()
    root_logger.addHandler(handler)

    # Quiet noisy third-party libraries
    for noisy_lib in ("httpx", "httpcore", "openai", "urllib3", "asyncio"):
        logging.getLogger(noisy_lib).setLevel(logging.WARNING)

    # ── 2. Configure structlog processors ─────────────────────────────────────
    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
    ]

    if log_format == "json":
        # Production: emit newline-delimited JSON
        shared_processors.append(structlog.processors.dict_tracebacks)
        renderer = structlog.processors.JSONRenderer()
    else:
        # Development: emit colourful, indented output
        renderer = structlog.dev.ConsoleRenderer(colors=True)  # type: ignore[assignment]

    structlog.configure(
        processors=shared_processors
        + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Attach structlog formatter to the stdlib handler
    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )
    handler.setFormatter(formatter)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Return a structlog bound logger for the given module name.

    Args:
        name: Typically __name__ of the calling module.

    Returns:
        A structlog BoundLogger with context binding support.

    Example:
        logger = get_logger(__name__)
        logger.info("workflow_started", query="LangGraph intro", session_id="abc123")
    """
    return structlog.get_logger(name)


def log_agent_start(agent_name: str, query: str) -> None:
    """Convenience helper to log the start of an agent execution."""
    logger = get_logger("agent")
    logger.info("agent_started", agent=agent_name, query_preview=query[:80])


def log_agent_end(agent_name: str, success: bool, duration_ms: float) -> None:
    """Convenience helper to log the completion of an agent execution."""
    logger = get_logger("agent")
    logger.info(
        "agent_completed",
        agent=agent_name,
        success=success,
        duration_ms=round(duration_ms, 2),
    )


def log_error(agent_name: str, error: Exception, context: dict | None = None) -> None:
    """Convenience helper to log an agent error with context."""
    logger = get_logger("agent")
    logger.error(
        "agent_error",
        agent=agent_name,
        error_type=type(error).__name__,
        error_message=str(error),
        context=context or {},
    )
