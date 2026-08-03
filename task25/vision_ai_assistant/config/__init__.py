"""config package — settings, constants, and logging."""

from config.settings import get_settings, Settings, BASE_DIR
from config.constants import (
    VisionModel,
    DocumentType,
    ChatRole,
    ExportFormat,
    VISION_MODELS,
    VISION_MODEL_LABELS,
    GROQ_MODELS,
    OPENAI_MODELS,
    DOCUMENT_TYPE_LABELS,
    DOCUMENT_TYPE_ICONS,
    SUPPORTED_IMAGE_FORMATS,
    PROMPT_CARDS,
    THEME,
    APP_ICON,
    DEFAULT_GREETING,
    EXPORT_FORMAT_LABELS,
)
from config.logging_config import setup_logging, get_logger

__all__ = [
    "get_settings",
    "Settings",
    "BASE_DIR",
    "VisionModel",
    "DocumentType",
    "ChatRole",
    "ExportFormat",
    "VISION_MODELS",
    "VISION_MODEL_LABELS",
    "GROQ_MODELS",
    "OPENAI_MODELS",
    "DOCUMENT_TYPE_LABELS",
    "DOCUMENT_TYPE_ICONS",
    "SUPPORTED_IMAGE_FORMATS",
    "PROMPT_CARDS",
    "THEME",
    "APP_ICON",
    "DEFAULT_GREETING",
    "EXPORT_FORMAT_LABELS",
    "setup_logging",
    "get_logger",
]
