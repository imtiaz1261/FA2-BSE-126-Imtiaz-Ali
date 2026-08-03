"""
config/constants.py
===================
All application-wide constants, enumerations, document type definitions,
supported models, and UI colour tokens.

Nothing here should import from any other project module to prevent
circular imports.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, List


# ---------------------------------------------------------------------------
# Supported Vision Models  (Groq primary + OpenAI fallback)
# ---------------------------------------------------------------------------
class VisionModel(str, Enum):
    # Groq text models (available on free tier)
    LLAMA33_70B     = "llama-3.3-70b-versatile"
    LLAMA31_8B      = "llama-3.1-8b-instant"
    GPT_OSS_120B    = "openai/gpt-oss-120b"
    GPT_OSS_20B     = "openai/gpt-oss-20b"
    # Groq vision models (requires vision-enabled account)
    LLAMA32_VISION  = "llama-3.2-11b-vision-preview"
    LLAMA32_VISION_90 = "llama-3.2-90b-vision-preview"
    # OpenAI models (optional)
    GPT_4O          = "gpt-4o"
    GPT_4O_MINI     = "gpt-4o-mini"


VISION_MODELS: List[str] = [m.value for m in VisionModel]

VISION_MODEL_LABELS: Dict[str, str] = {
    VisionModel.LLAMA33_70B:       "⚡ Llama 3.3 70B  (Groq · Recommended)",
    VisionModel.LLAMA31_8B:        "🚀 Llama 3.1 8B Instant  (Groq · Fast)",
    VisionModel.GPT_OSS_120B:      "🤖 GPT-OSS 120B  (Groq)",
    VisionModel.GPT_OSS_20B:       "🤖 GPT-OSS 20B  (Groq · Fast)",
    VisionModel.LLAMA32_VISION:    "👁️ Llama 3.2 11B Vision  (Groq · Vision)",
    VisionModel.LLAMA32_VISION_90: "👁️ Llama 3.2 90B Vision  (Groq · Vision)",
    VisionModel.GPT_4O:            "✨ GPT-4o  (OpenAI · Vision)",
    VisionModel.GPT_4O_MINI:       "✨ GPT-4o Mini  (OpenAI · Vision)",
}

# Which models run on Groq vs OpenAI
GROQ_MODELS: List[str] = [
    VisionModel.LLAMA33_70B,
    VisionModel.LLAMA31_8B,
    VisionModel.GPT_OSS_120B,
    VisionModel.GPT_OSS_20B,
    VisionModel.LLAMA32_VISION,
    VisionModel.LLAMA32_VISION_90,
]
OPENAI_MODELS: List[str] = [
    VisionModel.GPT_4O,
    VisionModel.GPT_4O_MINI,
]


# ---------------------------------------------------------------------------
# Document Types
# ---------------------------------------------------------------------------
class DocumentType(str, Enum):
    INVOICE       = "invoice"
    RECEIPT       = "receipt"
    BANK_STATEMENT = "bank_statement"
    BUSINESS_CARD = "business_card"
    DIAGRAM       = "diagram"
    FLOWCHART     = "flowchart"
    FORM          = "form"
    HANDWRITTEN   = "handwritten_note"
    MEDICAL       = "medical_report"
    ID_CARD       = "id_card"
    UNKNOWN       = "unknown"


DOCUMENT_TYPE_LABELS: Dict[str, str] = {
    DocumentType.INVOICE:        "Invoice",
    DocumentType.RECEIPT:        "Receipt",
    DocumentType.BANK_STATEMENT: "Bank Statement",
    DocumentType.BUSINESS_CARD:  "Business Card",
    DocumentType.DIAGRAM:        "Diagram",
    DocumentType.FLOWCHART:      "Flowchart",
    DocumentType.FORM:           "Form",
    DocumentType.HANDWRITTEN:    "Handwritten Note",
    DocumentType.MEDICAL:        "Medical Report",
    DocumentType.ID_CARD:        "ID Card",
    DocumentType.UNKNOWN:        "Unknown Document",
}

DOCUMENT_TYPE_ICONS: Dict[str, str] = {
    DocumentType.INVOICE:        "🧾",
    DocumentType.RECEIPT:        "🛒",
    DocumentType.BANK_STATEMENT: "🏦",
    DocumentType.BUSINESS_CARD:  "💼",
    DocumentType.DIAGRAM:        "📊",
    DocumentType.FLOWCHART:      "🔀",
    DocumentType.FORM:           "📋",
    DocumentType.HANDWRITTEN:    "✍️",
    DocumentType.MEDICAL:        "🏥",
    DocumentType.ID_CARD:        "🪪",
    DocumentType.UNKNOWN:        "📄",
}


# ---------------------------------------------------------------------------
# Supported Image Formats
# ---------------------------------------------------------------------------
SUPPORTED_IMAGE_FORMATS: List[str] = ["png", "jpg", "jpeg", "webp"]
SUPPORTED_MIME_TYPES: List[str] = [
    "image/png",
    "image/jpeg",
    "image/webp",
]


# ---------------------------------------------------------------------------
# Chat Roles
# ---------------------------------------------------------------------------
class ChatRole(str, Enum):
    USER      = "user"
    ASSISTANT = "assistant"
    SYSTEM    = "system"


# ---------------------------------------------------------------------------
# Export Formats
# ---------------------------------------------------------------------------
class ExportFormat(str, Enum):
    JSON     = "json"
    MARKDOWN = "markdown"
    PDF      = "pdf"
    DOCX     = "docx"
    TXT      = "txt"


EXPORT_FORMAT_LABELS: Dict[str, str] = {
    ExportFormat.JSON:     "JSON  (.json)",
    ExportFormat.MARKDOWN: "Markdown  (.md)",
    ExportFormat.PDF:      "PDF Report  (.pdf)",
    ExportFormat.DOCX:     "Word Document  (.docx)",
    ExportFormat.TXT:      "Plain Text  (.txt)",
}


# ---------------------------------------------------------------------------
# Prompt Card Suggestions (shown on empty state)
# ---------------------------------------------------------------------------
PROMPT_CARDS: List[Dict[str, str]] = [
    {
        "icon": "🧾",
        "title": "Extract Invoice Info",
        "prompt": "Extract all invoice information and return as structured JSON.",
    },
    {
        "icon": "📊",
        "title": "Summarize Diagram",
        "prompt": "Summarize this diagram. What does it represent? List all components and their relationships.",
    },
    {
        "icon": "✍️",
        "title": "Read Handwritten Notes",
        "prompt": "Transcribe all handwritten text in this image accurately.",
    },
    {
        "icon": "💰",
        "title": "Find Total Amount",
        "prompt": "What is the total amount shown in this document? Include currency.",
    },
    {
        "icon": "🔀",
        "title": "Explain Flowchart",
        "prompt": "Walk me through this flowchart step by step. What process does it describe?",
    },
    {
        "icon": "🗂️",
        "title": "Convert to JSON",
        "prompt": "Convert all visible information in this image into a structured JSON object.",
    },
    {
        "icon": "🏦",
        "title": "Analyze Bank Statement",
        "prompt": "Analyze this bank statement. List all transactions, dates, and balances.",
    },
    {
        "icon": "💼",
        "title": "Read Business Card",
        "prompt": "Extract all contact information from this business card as JSON.",
    },
]


# ---------------------------------------------------------------------------
# UI / Theme tokens
# ---------------------------------------------------------------------------
THEME = {
    "primary":          "#6366f1",   # Indigo
    "primary_hover":    "#4f46e5",
    "secondary":        "#8b5cf6",   # Violet
    "accent":           "#06b6d4",   # Cyan
    "success":          "#10b981",   # Emerald
    "warning":          "#f59e0b",   # Amber
    "error":            "#ef4444",   # Red
    "background":       "#0f0f23",   # Deep navy
    "surface":          "#1a1a2e",   # Card surface
    "surface_2":        "#16213e",   # Slightly lighter
    "border":           "#2d2d4e",
    "text_primary":     "#e2e8f0",
    "text_secondary":   "#94a3b8",
    "text_muted":       "#64748b",
    "user_bubble":      "#1e3a5f",   # User message bg
    "ai_bubble":        "#1a1a2e",   # AI message bg
    "code_bg":          "#0d1117",   # Code block bg
}


# ---------------------------------------------------------------------------
# Misc
# ---------------------------------------------------------------------------
APP_ICON          = "🔍"
DEFAULT_GREETING  = "Hello! Upload an image to get started. I can analyze invoices, receipts, diagrams, handwritten notes, and much more."
TYPING_INDICATOR  = "▌"
MAX_HISTORY_ITEMS = 20          # conversation history items shown in sidebar
STREAM_CHUNK_SIZE = 10          # chars per streaming chunk in demo mode
