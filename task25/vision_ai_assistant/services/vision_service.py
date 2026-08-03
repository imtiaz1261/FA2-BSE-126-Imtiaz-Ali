"""
services/vision_service.py
==========================
Handles everything related to image intake and initial VLM analysis.

Responsibilities:
  - Validate and process uploaded image bytes (Pillow)
  - Build UploadedImage with metadata + base64
  - Classify document type via VLM
  - Run initial analysis (shown immediately after upload)
  - Run structured extraction pipeline
"""

from __future__ import annotations

import json
import time
from io import BytesIO
from typing import Optional, Tuple

from loguru import logger
from PIL import Image, UnidentifiedImageError

from config.settings import get_settings
from config.constants import SUPPORTED_IMAGE_FORMATS, DocumentType
from models.document import (
    DocumentAnalysis,
    ExtractionResult,
    ImageMetadata,
    UploadedImage,
)
from prompts.templates import PromptBuilder


# ---------------------------------------------------------------------------
# Image processing helpers
# ---------------------------------------------------------------------------

def process_uploaded_file(
    file_bytes: bytes,
    filename: str,
) -> Tuple[UploadedImage, Optional[str]]:
    """
    Validate and convert raw uploaded bytes into an UploadedImage.

    Args:
        file_bytes: Raw bytes from Streamlit file_uploader
        filename:   Original filename (used to infer format)

    Returns:
        (UploadedImage, error_message)
        error_message is None on success, a string on failure.
    """
    settings = get_settings()

    # --- Size check ---
    if len(file_bytes) > settings.max_image_size_bytes:
        return None, (
            f"Image too large ({len(file_bytes) / 1024 / 1024:.1f} MB). "
            f"Maximum allowed: {settings.max_image_size_mb} MB."
        )

    # --- Format check ---
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in SUPPORTED_IMAGE_FORMATS:
        return None, (
            f"Unsupported format '{ext}'. "
            f"Supported: {', '.join(SUPPORTED_IMAGE_FORMATS).upper()}"
        )

    # --- Open with Pillow ---
    try:
        img = Image.open(BytesIO(file_bytes))
        img.verify()                          # detect truncated files
        img = Image.open(BytesIO(file_bytes)) # re-open after verify()
    except UnidentifiedImageError:
        return None, "Could not identify image format. Please upload a valid image file."
    except Exception as exc:
        return None, f"Image processing error: {exc}"

    # --- Normalise ---
    img_format = (img.format or ext).upper()
    if img_format == "JPG":
        img_format = "JPEG"

    # Convert RGBA/P/LA to RGB for JPEG compatibility
    if img.mode not in ("RGB", "RGBA", "L"):
        img = img.convert("RGB")

    # Re-encode to bytes for consistent base64
    buffer = BytesIO()
    save_format = img_format if img_format in ("PNG", "JPEG", "WEBP") else "PNG"
    if img.mode == "RGBA" and save_format == "JPEG":
        img = img.convert("RGB")
    img.save(buffer, format=save_format, optimize=True)
    processed_bytes = buffer.getvalue()

    # --- Build UploadedImage ---
    uploaded = UploadedImage.from_bytes(
        raw_bytes=processed_bytes,
        filename=filename,
        img_format=save_format,
        width=img.width,
        height=img.height,
        mode=img.mode,
    )

    logger.info(
        "Image processed: {} | {}×{} | {:.1f} KB | format={}",
        filename,
        img.width,
        img.height,
        len(processed_bytes) / 1024,
        save_format,
    )

    return uploaded, None


def resize_image_for_display(
    file_bytes: bytes,
    max_width: int = 800,
    max_height: int = 600,
) -> bytes:
    """
    Return resized image bytes suitable for Streamlit display.
    Does NOT modify the original — only used for the preview panel.
    """
    try:
        img = Image.open(BytesIO(file_bytes))
        img.thumbnail((max_width, max_height), Image.LANCZOS)
        buf = BytesIO()
        fmt = img.format or "PNG"
        if img.mode == "RGBA" and fmt == "JPEG":
            img = img.convert("RGB")
        img.save(buf, format=fmt)
        return buf.getvalue()
    except Exception:
        return file_bytes  # return original on failure


# ---------------------------------------------------------------------------
# VisionService
# ---------------------------------------------------------------------------

class VisionService:
    """
    Orchestrates image-based AI analysis using Groq or OpenAI Vision API.
    Automatically selects the right client based on configured keys.
    """

    def __init__(self, openai_client=None) -> None:
        """
        Args:
            openai_client: Optional pre-built client (Groq or OpenAI).
                           If None, the client is resolved from settings.
        """
        self._forced_client = openai_client
        self._settings = get_settings()

    def _get_client(self):
        """Return (client, model) using settings-based provider selection."""
        if self._forced_client:
            return self._forced_client, self._settings.default_model
        from services.llm_service import get_client
        client, provider = get_client(self._settings.default_model)
        return client, self._settings.default_model

    # ------------------------------------------------------------------
    # Document classification
    # ------------------------------------------------------------------
    def classify_document(
        self,
        image: UploadedImage,
    ) -> Tuple[str, float, str]:
        """
        Classify document type using the VLM (or text+OCR for text-only models).
        Returns: (document_type, confidence, language)
        """
        client, model = self._get_client()

        # Determine if vision is supported
        is_vision_model = model in [
            "llama-3.2-11b-vision-preview", "llama-3.2-90b-vision-preview",
            "meta-llama/llama-4-scout-17b-16e-instruct",
            "meta-llama/llama-4-maverick-17b-128e-instruct",
            "gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-4.1",
        ]

        if is_vision_model:
            messages = PromptBuilder.classify_document(image.data_uri)
        else:
            from services.ocr_service import get_image_description_prompt
            from prompts.system_prompts import get_system_prompt
            ocr_context = get_image_description_prompt(image.base64_data, image.metadata.filename)
            classify_text = (
                f"{ocr_context}\n\n"
                "Based on the extracted text above, classify this document. "
                "Return ONLY a JSON object:\n"
                '{"document_type": "<invoice|receipt|bank_statement|business_card|'
                'diagram|flowchart|form|handwritten_note|medical_report|id_card|unknown>", '
                '"confidence": <0.0-1.0>, "language": "<language>", '
                '"brief_description": "<one sentence>"}'
            )
            messages = [
                {"role": "system", "content": get_system_prompt("classify")},
                {"role": "user", "content": classify_text},
            ]

        try:
            start = time.monotonic()
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=256,
                temperature=0.0,
            )
            latency_ms = int((time.monotonic() - start) * 1000)
            raw = response.choices[0].message.content.strip()
            raw = _strip_code_fence(raw)

            data = json.loads(raw)
            doc_type   = data.get("document_type", "unknown")
            confidence = float(data.get("confidence", 0.5))
            language   = data.get("language", "English")

            known = {d.value for d in DocumentType}
            if doc_type not in known:
                doc_type = "unknown"

            logger.info(
                "Classified: type={} conf={:.0%} lang={} latency={}ms",
                doc_type, confidence, language, latency_ms,
            )
            return doc_type, confidence, language

        except json.JSONDecodeError as exc:
            logger.warning("Classification JSON parse failed: {}", exc)
            return "unknown", 0.0, "English"
        except Exception as exc:
            logger.error("Classification error: {}", exc)
            return "unknown", 0.0, "English"

    # ------------------------------------------------------------------
    # Initial analysis
    # ------------------------------------------------------------------
    def run_initial_analysis(
        self,
        image: UploadedImage,
        document_type: str,
        confidence: float,
        language: str,
    ) -> DocumentAnalysis:
        """Run the initial document analysis and return a DocumentAnalysis."""
        client, model = self._get_client()

        is_vision_model = model in [
            "llama-3.2-11b-vision-preview", "llama-3.2-90b-vision-preview",
            "meta-llama/llama-4-scout-17b-16e-instruct",
            "meta-llama/llama-4-maverick-17b-128e-instruct",
            "gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-4.1",
        ]

        if is_vision_model:
            messages = PromptBuilder.initial_analysis(image.data_uri)
        else:
            from services.ocr_service import get_image_description_prompt
            from prompts.system_prompts import get_system_prompt
            from prompts.analysis_prompts import INITIAL_ANALYSIS_PROMPT
            ocr_context = get_image_description_prompt(image.base64_data, image.metadata.filename)
            messages = [
                {"role": "system", "content": get_system_prompt("main")},
                {"role": "user", "content": f"{ocr_context}\n\n{INITIAL_ANALYSIS_PROMPT}"},
            ]

        try:
            start = time.monotonic()
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=self._settings.max_tokens,
                temperature=self._settings.temperature,
            )
            latency_ms = int((time.monotonic() - start) * 1000)
            summary    = response.choices[0].message.content.strip()
            tokens     = response.usage.total_tokens if response.usage else 0

            logger.info("Initial analysis complete | tokens={} latency={}ms", tokens, latency_ms)

            return DocumentAnalysis(
                image_sha256=image.sha256,
                image_filename=image.metadata.filename,
                document_type=document_type,
                document_type_confidence=confidence,
                initial_summary=summary,
                language_detected=language,
                model_used=model,
                tokens_used=tokens,
                latency_ms=latency_ms,
            )

        except Exception as exc:
            logger.error("Initial analysis error: {}", exc)
            return DocumentAnalysis(
                image_sha256=image.sha256,
                image_filename=image.metadata.filename,
                document_type=document_type,
                document_type_confidence=confidence,
                initial_summary="",
                language_detected=language,
                model_used=model,
                error=str(exc),
            )

    # ------------------------------------------------------------------
    # Full pipeline: process image → classify → analyse → extract
    # ------------------------------------------------------------------
    def full_pipeline(
        self,
        image: UploadedImage,
        session_id: str,
    ) -> Tuple[DocumentAnalysis, str]:
        """
        Run the complete initial pipeline:
          1. Classify document type
          2. Run initial analysis

        Returns:
            (DocumentAnalysis, initial_summary_text)
        """
        doc_type, confidence, language = self.classify_document(image)
        analysis = self.run_initial_analysis(
            image, doc_type, confidence, language
        )
        return analysis, analysis.initial_summary


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def _strip_code_fence(text: str) -> str:
    """
    Remove markdown ```json ... ``` or ``` ... ``` wrappers from a string.
    Returns the inner content.
    """
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first line (```json or ```) and last line (```)
        inner = lines[1:-1] if lines[-1].strip() == "```" else lines[1:]
        return "\n".join(inner).strip()
    return text
