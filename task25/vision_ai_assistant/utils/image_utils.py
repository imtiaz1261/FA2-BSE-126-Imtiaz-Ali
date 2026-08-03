"""
utils/image_utils.py
====================
Image display and processing utilities for the Streamlit UI.

All functions here are pure helpers — they take bytes / PIL images
and return bytes / metadata dicts. No Streamlit calls inside.
"""

from __future__ import annotations

import base64
from io import BytesIO
from typing import Dict, Optional, Tuple

from loguru import logger
from PIL import Image, ImageDraw, ImageFont, ExifTags


# ---------------------------------------------------------------------------
# Thumbnail generation
# ---------------------------------------------------------------------------

def make_thumbnail(
    image_bytes: bytes,
    size: Tuple[int, int] = (400, 300),
    format: str = "JPEG",
) -> bytes:
    """
    Generate a thumbnail from image bytes.

    Args:
        image_bytes: Raw image data
        size:        Max (width, height) — aspect ratio preserved
        format:      Output format (JPEG, PNG, WEBP)

    Returns:
        Thumbnail bytes
    """
    try:
        img = Image.open(BytesIO(image_bytes))
        img.thumbnail(size, Image.LANCZOS)
        if img.mode == "RGBA" and format == "JPEG":
            img = img.convert("RGB")
        buf = BytesIO()
        img.save(buf, format=format, quality=85, optimize=True)
        return buf.getvalue()
    except Exception as exc:
        logger.warning("Thumbnail generation failed: {}", exc)
        return image_bytes


def make_display_image(
    image_bytes: bytes,
    max_width: int = 900,
    max_height: int = 700,
) -> bytes:
    """
    Resize an image to fit within max dimensions while preserving aspect ratio.
    Returns the resized image as JPEG bytes for fast display.
    """
    try:
        img = Image.open(BytesIO(image_bytes))
        original_format = img.format or "PNG"

        # Only resize if larger than limits
        if img.width > max_width or img.height > max_height:
            img.thumbnail((max_width, max_height), Image.LANCZOS)

        if img.mode == "RGBA":
            # Compose onto white background for JPEG
            bg = Image.new("RGB", img.size, (255, 255, 255))
            bg.paste(img, mask=img.split()[3])
            img = bg
        elif img.mode not in ("RGB", "L"):
            img = img.convert("RGB")

        buf = BytesIO()
        save_fmt = "JPEG" if original_format == "JPEG" else "PNG"
        quality_kwargs = {"quality": 90, "optimize": True} if save_fmt == "JPEG" else {}
        img.save(buf, format=save_fmt, **quality_kwargs)
        return buf.getvalue()
    except Exception as exc:
        logger.warning("Display image preparation failed: {}", exc)
        return image_bytes


# ---------------------------------------------------------------------------
# Base64 helpers for Streamlit HTML embedding
# ---------------------------------------------------------------------------

def bytes_to_base64_img_tag(
    image_bytes: bytes,
    mime: str = "image/jpeg",
    alt: str = "Document preview",
    css_class: str = "",
    style: str = "",
) -> str:
    """
    Wrap image bytes as an inline <img> HTML tag using base64 data URI.
    Used for custom-styled image display in Streamlit st.markdown().
    """
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    class_attr = f'class="{css_class}"' if css_class else ""
    style_attr = f'style="{style}"' if style else ""
    return (
        f'<img src="data:{mime};base64,{b64}" '
        f'alt="{alt}" {class_attr} {style_attr}/>'
    )


def image_to_base64_str(image_bytes: bytes) -> str:
    """Return plain base64 string (no data URI prefix)."""
    return base64.b64encode(image_bytes).decode("utf-8")


# ---------------------------------------------------------------------------
# Image metadata extraction
# ---------------------------------------------------------------------------

def get_image_info(image_bytes: bytes, filename: str = "") -> Dict[str, str]:
    """
    Extract human-readable image metadata.

    Returns a flat dict of display-ready strings.
    """
    try:
        img = Image.open(BytesIO(image_bytes))
        size_kb = len(image_bytes) / 1024
        size_str = f"{size_kb:.1f} KB" if size_kb < 1024 else f"{size_kb/1024:.2f} MB"

        info = {
            "Filename":    filename or "Unknown",
            "Format":      img.format or "Unknown",
            "Dimensions":  f"{img.width} × {img.height} px",
            "Mode":        img.mode,
            "File Size":   size_str,
            "Aspect Ratio": _aspect_ratio(img.width, img.height),
        }

        # Add EXIF data if available (JPEG)
        exif_data = _extract_exif(img)
        if exif_data:
            info.update(exif_data)

        return info
    except Exception as exc:
        logger.debug("Image info extraction failed: {}", exc)
        return {"Filename": filename, "Error": str(exc)}


def _extract_exif(img: Image.Image) -> Dict[str, str]:
    """Extract selected EXIF tags as a flat string dict."""
    result: Dict[str, str] = {}
    try:
        exif_raw = img._getexif()  # type: ignore[attr-defined]
        if not exif_raw:
            return result
        WANTED = {
            "DateTime":          "Date Taken",
            "Make":              "Camera Make",
            "Model":             "Camera Model",
            "Software":          "Software",
            "ImageDescription":  "Description",
        }
        tag_map = {v: k for k, v in ExifTags.TAGS.items()}
        for label, display in WANTED.items():
            tag_id = tag_map.get(label)
            if tag_id and tag_id in exif_raw:
                result[display] = str(exif_raw[tag_id])
    except Exception:
        pass
    return result


def _aspect_ratio(w: int, h: int) -> str:
    from math import gcd
    g = gcd(w, h)
    return f"{w // g}:{h // g}"


# ---------------------------------------------------------------------------
# Image annotation (draw bounding boxes for OCR regions)
# ---------------------------------------------------------------------------

def draw_annotation_box(
    image_bytes: bytes,
    boxes: list[Tuple[int, int, int, int]],
    labels: Optional[list[str]] = None,
    color: str = "#6366f1",
    line_width: int = 2,
) -> bytes:
    """
    Draw labelled bounding boxes on an image copy.

    Args:
        image_bytes: Source image
        boxes:       List of (x0, y0, x1, y1) tuples
        labels:      Optional label for each box
        color:       Box colour (hex or name)
        line_width:  Rectangle stroke width

    Returns:
        Annotated image as PNG bytes
    """
    try:
        img = Image.open(BytesIO(image_bytes)).convert("RGB")
        draw = ImageDraw.Draw(img)

        for i, (x0, y0, x1, y1) in enumerate(boxes):
            draw.rectangle([x0, y0, x1, y1], outline=color, width=line_width)
            if labels and i < len(labels):
                # Draw label background
                label = labels[i]
                draw.text((x0 + 4, y0 + 2), label, fill=color)

        buf = BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    except Exception as exc:
        logger.warning("Annotation failed: {}", exc)
        return image_bytes


# ---------------------------------------------------------------------------
# Format validation helpers
# ---------------------------------------------------------------------------

def is_valid_image_bytes(data: bytes) -> bool:
    """Return True if data is a readable image."""
    try:
        img = Image.open(BytesIO(data))
        img.verify()
        return True
    except Exception:
        return False


def get_image_mime_type(filename: str) -> str:
    """Infer MIME type from filename extension."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    mime_map = {
        "jpg":  "image/jpeg",
        "jpeg": "image/jpeg",
        "png":  "image/png",
        "webp": "image/webp",
        "gif":  "image/gif",
    }
    return mime_map.get(ext, "image/jpeg")
