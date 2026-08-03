"""
models/document.py
==================
Schemas for uploaded images and the analysis result produced by the
Vision Language Model.

UploadedImage    — raw image metadata + base64 payload
DocumentAnalysis — full VLM response, detected type, confidence
ExtractionResult — wrapper that ties analysis to structured extraction
"""

from __future__ import annotations

import base64
import hashlib
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from pydantic import BaseModel, Field, computed_field


# ---------------------------------------------------------------------------
# Uploaded image
# ---------------------------------------------------------------------------
class ImageMetadata(BaseModel):
    """Lightweight image info (no binary payload)."""

    filename: str
    format: str                  # "PNG", "JPEG", …
    width: int
    height: int
    size_bytes: int
    mode: str = "RGB"            # PIL mode
    uploaded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def size_kb(self) -> float:
        return round(self.size_bytes / 1024, 1)

    @property
    def size_mb(self) -> float:
        return round(self.size_bytes / (1024 * 1024), 2)

    @property
    def dimensions_str(self) -> str:
        return f"{self.width} × {self.height} px"

    @property
    def aspect_ratio(self) -> str:
        from math import gcd
        g = gcd(self.width, self.height)
        return f"{self.width // g}:{self.height // g}"


class UploadedImage(BaseModel):
    """
    Full image container: metadata + base64-encoded bytes.
    The base64 payload is what we send to the OpenAI Vision API.
    """

    metadata: ImageMetadata
    base64_data: str = Field(description="Base64-encoded image bytes")
    sha256: str = Field(description="SHA-256 hex digest for dedup")

    # ------------------------------------------------------------------
    @classmethod
    def from_bytes(
        cls,
        raw_bytes: bytes,
        filename: str,
        img_format: str,
        width: int,
        height: int,
        mode: str = "RGB",
    ) -> "UploadedImage":
        """Factory: build from raw image bytes."""
        sha = hashlib.sha256(raw_bytes).hexdigest()
        b64 = base64.b64encode(raw_bytes).decode("utf-8")
        meta = ImageMetadata(
            filename=filename,
            format=img_format.upper(),
            width=width,
            height=height,
            size_bytes=len(raw_bytes),
            mode=mode,
        )
        return cls(metadata=meta, base64_data=b64, sha256=sha)

    # ------------------------------------------------------------------
    @property
    def data_uri(self) -> str:
        """
        RFC 2397 data URI — used directly in the OpenAI vision messages.
        e.g.  data:image/jpeg;base64,/9j/4AAQSkZJRgAB…
        """
        fmt = self.metadata.format.lower()
        if fmt == "jpg":
            fmt = "jpeg"
        return f"data:image/{fmt};base64,{self.base64_data}"

    @property
    def mime_type(self) -> str:
        fmt = self.metadata.format.lower()
        if fmt in ("jpg", "jpeg"):
            return "image/jpeg"
        if fmt == "png":
            return "image/png"
        if fmt == "webp":
            return "image/webp"
        return f"image/{fmt}"

    def to_pil(self):
        """Return a PIL Image object (requires Pillow)."""
        from PIL import Image
        raw = base64.b64decode(self.base64_data)
        return Image.open(BytesIO(raw))


# ---------------------------------------------------------------------------
# VLM Analysis result
# ---------------------------------------------------------------------------
class DocumentAnalysis(BaseModel):
    """
    The structured result of running an image through the Vision LLM.
    """

    image_sha256: str = Field(description="Links back to UploadedImage")
    image_filename: str

    # Detected document type
    document_type: str = Field(
        default="unknown",
        description="One of the DocumentType enum values",
    )
    document_type_confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Model's confidence in the detected type (0-1)",
    )

    # Raw LLM outputs
    initial_summary: str = Field(
        default="",
        description="Brief description of the document",
    )
    full_text: str = Field(
        default="",
        description="All text extracted by OCR/VLM",
    )
    language_detected: str = Field(
        default="English",
        description="Primary language of the document",
    )

    # Structured extraction (JSON string)
    extracted_json: Optional[str] = Field(
        default=None,
        description="JSON string of structured extracted fields",
    )

    # Processing metadata
    model_used: str = Field(default="")
    tokens_used: int = Field(default=0)
    latency_ms: int = Field(default=0)
    analysed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    error: Optional[str] = Field(default=None)

    @property
    def has_error(self) -> bool:
        return self.error is not None

    @property
    def confidence_pct(self) -> str:
        return f"{int(self.document_type_confidence * 100)}%"

    @property
    def extracted_data(self) -> Optional[Dict[str, Any]]:
        """Parse extracted_json back to a dict, or None on failure."""
        if not self.extracted_json:
            return None
        import json
        try:
            return json.loads(self.extracted_json)
        except json.JSONDecodeError:
            return None


# ---------------------------------------------------------------------------
# Full extraction result (ties image + analysis + typed extraction)
# ---------------------------------------------------------------------------
class ExtractionResult(BaseModel):
    """
    Top-level object returned by the extraction pipeline.
    Passed around the app and used for export.
    """

    session_id: str
    image: UploadedImage
    analysis: DocumentAnalysis
    raw_extraction: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Parsed structured extraction dict",
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def document_type(self) -> str:
        return self.analysis.document_type

    @property
    def summary(self) -> str:
        return self.analysis.initial_summary

    def to_export_dict(self) -> Dict[str, Any]:
        """Flat dict suitable for JSON/Markdown export."""
        return {
            "session_id": self.session_id,
            "image_filename": self.image.metadata.filename,
            "document_type": self.document_type,
            "language": self.analysis.language_detected,
            "summary": self.summary,
            "extracted_text": self.analysis.full_text,
            "structured_data": self.raw_extraction,
            "model_used": self.analysis.model_used,
            "analysed_at": self.analysis.analysed_at.isoformat(),
        }
