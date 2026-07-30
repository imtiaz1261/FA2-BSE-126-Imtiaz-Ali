"""
Centralized logging utility for the RAG Evaluation Pipeline.

Every module in the project should obtain its logger via `get_logger(__name__)`
rather than configuring `logging` directly. This guarantees a single, consistent
log format across the entire codebase and makes it trivial to redirect all
output to a file for later debugging or audit purposes.
"""

from __future__ import annotations

import logging
import sys
from logging import Logger
from pathlib import Path

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_configured_loggers: dict[str, Logger] = {}


def get_logger(
    name: str,
    level: str = "INFO",
    log_to_file: bool = False,
    log_file_path: str | Path = "./logs/pipeline.log",
) -> Logger:
    """
    Return a configured logger instance for the given module name.

    Args:
        name: Typically `__name__` of the calling module.
        level: Logging level as a string (e.g. "INFO", "DEBUG", "WARNING").
        log_to_file: If True, also write logs to `log_file_path`.
        log_file_path: Path to the log file (parent directories are created
            automatically).

    Returns:
        A configured `logging.Logger` instance. Repeated calls with the same
        `name` return the same logger without duplicating handlers.
    """
    if name in _configured_loggers:
        return _configured_loggers[name]

    logger = logging.getLogger(name)
    logger.setLevel(level.upper())
    logger.propagate = False

    formatter = logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)

    # Console handler
    console_handler = logging.StreamHandler(stream=sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Optional file handler
    if log_to_file:
        file_path = Path(log_file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(file_path, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    _configured_loggers[name] = logger
    return logger
