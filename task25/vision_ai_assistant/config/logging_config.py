"""
config/logging_config.py
========================
Centralised logging setup using loguru.

Call `setup_logging()` once at application startup (in app.py).
All other modules then simply do:

    from loguru import logger
    logger.info("...")

Loguru is sink-based — we add two sinks:
  1. stderr  — for development / console visibility
  2. file    — rotating daily log file inside logs/
"""

from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger

from config.settings import get_settings

BASE_DIR = Path(__file__).resolve().parent.parent
LOGS_DIR = BASE_DIR / "logs"


def setup_logging() -> None:
    """
    Configure loguru sinks.
    Must be called once, at process start.
    """
    settings = get_settings()
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    # Remove the default sink so we control the format precisely
    logger.remove()

    # ----------------------------------------------------------------
    # Console sink
    # ----------------------------------------------------------------
    log_level = "DEBUG" if settings.debug else "INFO"

    logger.add(
        sys.stderr,
        level=log_level,
        colorize=True,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> — "
            "<level>{message}</level>"
        ),
        backtrace=True,
        diagnose=settings.debug,
    )

    # ----------------------------------------------------------------
    # File sink — rotates daily, keeps 7 days
    # ----------------------------------------------------------------
    logger.add(
        LOGS_DIR / "vision_ai_{time:YYYY-MM-DD}.log",
        level="DEBUG",
        rotation="00:00",        # rotate at midnight
        retention="7 days",
        compression="zip",
        format=(
            "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
            "{level: <8} | "
            "{name}:{function}:{line} — {message}"
        ),
        backtrace=True,
        diagnose=False,          # keep file logs safe (no local var dumps)
        encoding="utf-8",
    )

    logger.info(
        "Logging initialised | level={} | debug={}",
        log_level,
        settings.debug,
    )


def get_logger(name: str):
    """
    Return a loguru logger bound to a specific module name.
    Usage:  log = get_logger(__name__)
    """
    return logger.bind(module=name)
