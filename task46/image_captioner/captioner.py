"""
Core image captioning logic — separated from the CLI so it can be
reused, tested, or wrapped in a different interface later.
"""

import sys
import os
import base64
from openai import OpenAI
from config import LLM_PROVIDER, GROQ_API_KEY, OPENAI_API_KEY, VISION_MODEL_NAME

SUPPORTED_EXTENSIONS = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
}

MAX_IMAGE_SIZE_MB = 20  # matches Groq's documented per-image limit


class CaptionError(Exception):
    """Raised when image validation or caption generation fails."""


def get_client() -> OpenAI:
    """Build an OpenAI-compatible client pointed at the configured provider."""
    if LLM_PROVIDER == "groq":
        if not GROQ_API_KEY:
            sys.exit(
                "ERROR: GROQ_API_KEY is missing.\n"
                "Get a free key at https://console.groq.com/keys and add it "
                "to your .env file (GROQ_API_KEY=...)."
            )
        return OpenAI(
            api_key=GROQ_API_KEY,
            base_url="https://api.groq.com/openai/v1",
        )

    if LLM_PROVIDER == "openai":
        if not OPENAI_API_KEY:
            sys.exit(
                "ERROR: OPENAI_API_KEY is missing.\n"
                "Add it to your .env file, or set LLM_PROVIDER=groq to use "
                "the free Groq API instead."
            )
        return OpenAI(api_key=OPENAI_API_KEY)

    sys.exit(f"ERROR: Unknown LLM_PROVIDER '{LLM_PROVIDER}'. Use 'groq' or 'openai'.")


def validate_image_path(image_path: str) -> str:
    """
    Checks the path exists, has a supported extension, and isn't too
    large. Returns the detected MIME type on success.
    """
    if not image_path or not image_path.strip():
        raise CaptionError("Image path cannot be empty.")

    if not os.path.isfile(image_path):
        raise CaptionError(f"File not found: {image_path}")

    _, ext = os.path.splitext(image_path.lower())
    if ext not in SUPPORTED_EXTENSIONS:
        supported = ", ".join(SUPPORTED_EXTENSIONS.keys())
        raise CaptionError(
            f"Unsupported file type '{ext}'. Supported types: {supported}"
        )

    size_mb = os.path.getsize(image_path) / (1024 * 1024)
    if size_mb > MAX_IMAGE_SIZE_MB:
        raise CaptionError(
            f"Image is {size_mb:.1f} MB, which exceeds the {MAX_IMAGE_SIZE_MB} MB limit."
        )

    return SUPPORTED_EXTENSIONS[ext]


def _encode_image_as_data_url(image_path: str, mime_type: str) -> str:
    with open(image_path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("utf-8")
    return f"data:{mime_type};base64,{encoded}"


def caption_image(client: OpenAI, image_path: str) -> str:
    """
    Generate a short, descriptive caption for the image at `image_path`
    using a vision-capable LLM.

    Raises CaptionError on invalid input, file issues, or API failure.
    """
    mime_type = validate_image_path(image_path)
    data_url = _encode_image_as_data_url(image_path, mime_type)

    try:
        response = client.chat.completions.create(
            model=VISION_MODEL_NAME,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "Write one short, descriptive caption for this "
                                "image, in a single sentence. Do not add "
                                "quotation marks or a trailing period-only "
                                "explanation — just the caption itself."
                            ),
                        },
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                }
            ],
            temperature=0.4,
        )
    except Exception as e:
        raise CaptionError(f"Caption generation request failed: {e}") from e

    caption = response.choices[0].message.content.strip()
    if not caption:
        raise CaptionError("Model returned an empty caption.")

    return caption
