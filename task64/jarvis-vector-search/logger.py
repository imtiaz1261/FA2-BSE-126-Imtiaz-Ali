"""
logger.py
---------
Central logger factory. Log level is configurable via the LOG_LEVEL
environment variable (DEBUG, INFO, WARNING, ERROR). Defaults to INFO.
"""
import logging
import os
import sys

_CONFIGURED = False


def get_logger(name: str = "jarvis.vector_search") -> logging.Logger:
    global _CONFIGURED
    logger = logging.getLogger(name)

    if not _CONFIGURED:
        level_name = os.getenv("LOG_LEVEL", "INFO").upper()
        level = getattr(logging, level_name, logging.INFO)

        root = logging.getLogger("jarvis")
        root.setLevel(level)

        if not root.handlers:
            handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter(
                fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            handler.setFormatter(formatter)
            root.addHandler(handler)

        _CONFIGURED = True

    return logger
