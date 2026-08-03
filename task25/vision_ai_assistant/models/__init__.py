"""models package — all Pydantic schemas."""

# Chat schemas
from models.chat import (
    ChatMessage,
    ChatSession,
    ConversationSummary,
    ConversationHistory,
)

# Document schemas
from models.document import (
    ImageMetadata,
    UploadedImage,
    DocumentAnalysis,
    ExtractionResult,
)

# Extraction schemas
from models.extraction import (
    LineItem,
    BankTransaction,
    Address,
    InvoiceExtraction,
    ReceiptExtraction,
    BankStatementExtraction,
    BusinessCardExtraction,
    DiagramExtraction,
    FormExtraction,
    HandwrittenExtraction,
    MedicalReportExtraction,
    IDCardExtraction,
    GenericExtraction,
    EXTRACTION_SCHEMA_MAP,
    get_extraction_schema,
    get_empty_extraction,
)

__all__ = [
    # chat
    "ChatMessage",
    "ChatSession",
    "ConversationSummary",
    "ConversationHistory",
    # document
    "ImageMetadata",
    "UploadedImage",
    "DocumentAnalysis",
    "ExtractionResult",
    # extraction
    "LineItem",
    "BankTransaction",
    "Address",
    "InvoiceExtraction",
    "ReceiptExtraction",
    "BankStatementExtraction",
    "BusinessCardExtraction",
    "DiagramExtraction",
    "FormExtraction",
    "HandwrittenExtraction",
    "MedicalReportExtraction",
    "IDCardExtraction",
    "GenericExtraction",
    "EXTRACTION_SCHEMA_MAP",
    "get_extraction_schema",
    "get_empty_extraction",
]
