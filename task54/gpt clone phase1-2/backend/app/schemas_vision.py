"""
Schemas for Image Understanding (Vision) module.

Includes request/response schemas for:
- Vision Q&A (free-form image understanding)
- Vision extraction (structured data from images)
- Image upload and storage
"""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ============================================================================
# Image Upload
# ============================================================================


class ImageUploadResponse(BaseModel):
    """Response after uploading an image."""

    image_id: UUID = Field(description="Unique image ID")
    filename: str = Field(description="Original filename")
    file_type: str = Field(description="JPEG, PNG, WebP, or GIF")
    file_size_bytes: int = Field(description="File size in bytes")
    signed_url: str = Field(description="Time-limited S3 signed URL")
    signed_url_expires_at: datetime = Field(description="When signed URL expires")
    metadata: dict = Field(default_factory=dict, description="Image dimensions, etc.")

    class Config:
        from_attributes = True


class ImageMetadata(BaseModel):
    """Metadata for an image."""

    id: UUID
    filename: str
    file_type: str
    file_size_bytes: int
    signed_url: str
    signed_url_expires_at: datetime
    metadata: dict
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Vision Q&A (Free-form)
# ============================================================================


class VisionQARequest(BaseModel):
    """Question/Answer request with one or more images."""

    image_ids: list[UUID] = Field(
        min_items=1,
        description="One or more uploaded image IDs",
    )
    question: str = Field(
        min_length=1,
        max_length=2000,
        description="Question about the image(s)",
    )
    conversation_id: Optional[UUID] = Field(
        None, description="Associate with conversation"
    )


class VisionQAResponse(BaseModel):
    """Response with vision-generated answer."""

    request_id: UUID = Field(description="Vision request ID")
    answer: str = Field(description="Model-generated answer")
    images_processed: list[UUID] = Field(description="Image IDs used")
    confidence: Optional[float] = Field(None, ge=0, le=1)
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Vision Extraction (Structured)
# ============================================================================


class ExtractionSchema(BaseModel):
    """Schema for structured extraction mode."""

    type: str = Field(
        description="Type of extraction: 'receipt', 'form', 'table', 'custom'"
    )
    fields: Optional[dict] = Field(
        None,
        description="For 'custom': dict of {field_name: field_type}. "
        "field_type can be 'string', 'number', 'date', 'list'",
    )


class VisionExtractionRequest(BaseModel):
    """Structured extraction request from image(s)."""

    image_ids: list[UUID] = Field(
        min_items=1,
        description="One or more uploaded image IDs",
    )
    extraction_type: str = Field(
        description="Type: 'receipt' (line items, total), "
        "'form' (fields/values), 'table' (rows/cols), 'custom'",
    )
    custom_schema: Optional[dict] = Field(
        None,
        description="For extraction_type='custom': "
        "{field_name: 'string'|'number'|'date'|'list'}",
    )
    conversation_id: Optional[UUID] = Field(None)


class ExtractionResult(BaseModel):
    """Structured extraction result."""

    request_id: UUID
    extraction_type: str
    data: dict = Field(description="Extracted data matching schema")
    confidence_scores: Optional[dict] = Field(
        None, description="Per-field confidence scores"
    )
    images_processed: list[UUID]
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Vision Request Status
# ============================================================================


class VisionRequestStatus(BaseModel):
    """Status of a vision request."""

    request_id: UUID
    status: str  # pending, completed, failed
    request_type: str  # qa or extract
    response: Optional[str] = None
    extraction_result: Optional[dict] = None
    error_message: Optional[str] = None
    images_used: list[UUID]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Error Responses
# ============================================================================


class ImageErrorDetail(BaseModel):
    """Detail about a specific image error."""

    image_index: int = Field(description="0-based index in upload batch")
    filename: str
    error_code: str = Field(
        description="'unsupported_format', 'file_too_large', 'invalid_image', etc."
    )
    error_message: str


class ImageValidationError(BaseModel):
    """Validation error for image uploads."""

    errors: list[ImageErrorDetail]

    class Config:
        from_attributes = True
