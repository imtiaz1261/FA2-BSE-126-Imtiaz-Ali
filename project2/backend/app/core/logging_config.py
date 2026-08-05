"""
Centralized logging configuration for the backend.

Call `configure_logging()` once, on app startup (done in `main.py`).
Every module should then just do:

    import logging
    logger = logging.getLogger(__name__)
"""

import logging
import sys

from app.core.config import settings


def configure_logging() -> None:
    root = logging.getLogger()
    root.setLevel(settings.LOG_LEVEL)

    # Avoid duplicate handlers on reload
    if root.handlers:
        return

    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    root.addHandler(handler)

    # Quiet down noisy third-party loggers by default
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
