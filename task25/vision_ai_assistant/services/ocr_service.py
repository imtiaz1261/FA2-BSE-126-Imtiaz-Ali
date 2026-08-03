"""
services/ocr_service.py
========================
OCR extraction using pytesseract (if available) or PIL-based fallback.
Used when the LLM provider doesn't support vision/image input.
"""

from __future__ import annotations

import base64
from io import BytesIO
from typing import Optional

from loguru import logger


def extract_text_from_image(base64_data: str) -> str:
    """
    Extract text from a base64-encoded image.
    Tries pytesseract first, falls back to a placeholder.
    
    Returns extracted text string.
    """
    raw = base64.b64decode(base64_data)
    
    # --- Try pytesseract ---
    try:
        import pytesseract
        from PIL import Image
        img = Image.open(BytesIO(raw))
        text = pytesseract.image_to_string(img)
        if text.strip():
            logger.info("OCR via pytesseract: {} chars", len(text))
            return text.strip()
    except ImportError:
        logger.debug("pytesseract not available")
    except Exception as exc:
        logger.debug("pytesseract failed: {}", exc)

    # --- Try easyocr ---
    try:
        import easyocr
        import numpy as np
        from PIL import Image
        img = Image.open(BytesIO(raw)).convert("RGB")
        arr = np.array(img)
        reader = easyocr.Reader(["en"], gpu=False, verbose=False)
        results = reader.readtext(arr, detail=0)
        text = "\n".join(results)
        if text.strip():
            logger.info("OCR via easyocr: {} chars", len(text))
            return text.strip()
    except ImportError:
        logger.debug("easyocr not available")
    except Exception as exc:
        logger.debug("easyocr failed: {}", exc)

    # --- Fallback: return empty string ---
    logger.warning("No OCR engine available — returning empty text")
    return ""


def get_image_description_prompt(base64_data: str, filename: str = "") -> str:
    """
    Build a text prompt that embeds image info for a text-only LLM.
    Includes OCR-extracted text if available.
    """
    ocr_text = extract_text_from_image(base64_data)
    
    fname_line = f"Filename: {filename}\n" if filename else ""
    
    if ocr_text:
        return (
            f"[DOCUMENT IMAGE]\n"
            f"{fname_line}"
            f"The following text was extracted from the document image via OCR:\n\n"
            f"--- BEGIN EXTRACTED TEXT ---\n"
            f"{ocr_text}\n"
            f"--- END EXTRACTED TEXT ---\n\n"
            f"Based on the above extracted text, please answer the user's question."
        )
    else:
        return (
            f"[DOCUMENT IMAGE]\n"
            f"{fname_line}"
            f"An image was uploaded but OCR text extraction was not available. "
            f"Please inform the user that this model requires a vision-capable API "
            f"(such as OpenAI GPT-4o) to analyse images directly. "
            f"Suggest they add an OpenAI API key in Settings."
        )
