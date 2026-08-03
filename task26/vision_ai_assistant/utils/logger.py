"""Centralized application logging utilities."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from logging import Logger
from pathlib import Path


def configure_logging(level: str = "INFO", logs_dir: str = "logs") -> None:
    """Configure global logging with console and rotating file handlers."""
    root_logger = logging.getLogger()
    resolved_level = getattr(logging, level.upper(), logging.INFO)

    if root_logger.handlers:
        root_logger.setLevel(resolved_level)
        return

    log_path = Path(logs_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    file_handler = RotatingFileHandler(
        filename=log_path / "app.log",
        maxBytes=1_048_576,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    root_logger.setLevel(resolved_level)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)


def get_logger(name: str) -> Logger:
    """Return a logger instance for the given module."""
    return logging.getLogger(name)
