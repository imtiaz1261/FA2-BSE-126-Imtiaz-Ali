"""
Vision LLM service for image understanding.

Supports multimodal LLM APIs (GPT-4V, Claude 3 Vision, etc.)
Handles Q&A and structured extraction modes.
"""

import json
import logging
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)

# ============================================================================
# Vision LLM Service
# ============================================================================


class VisionLLMService:
    """Process images with vision-capable LLM."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """Initialize vision LLM service."""
        self.api_key = api_key or settings.vision_api_key
        self.model = model or settings.vision_model

        if not self.api_key:
            raise ValueError("Vision API key not configured")

        # Initialize appropriate client
        if "gpt" in self.model.lower() or "vision" in self.model.lower():
            self._init_openai()
        elif "claude" in self.model.lower():
            self._init_anthropic()
        else:
            raise ValueError(f"Unknown vision model: {self.model}")

    def _init_openai(self):
        """Initialize OpenAI GPT-4V client."""
        import openai

        openai.api_key = self.api_key
        self.client = openai
        self.provider = "openai"

    def _init_anthropic(self):
        """Initialize Anthropic Claude Vision client."""
        import anthropic

        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.provider = "anthropic"

    # ============================================================================
    # Image Understanding (Q&A)
    # ============================================================================

    def understand_image(
        self,
        image_urls: list[str],
        question: str,
        max_tokens: int = 1024,
    ) -> Optional[str]:
        """
        Answer a question about one or more images.

        Args:
            image_urls: List of image URLs (should be signed S3 URLs)
            question: Question about the image(s)
            max_tokens: Max response length

        Returns:
            Answer text or None if failed
        """
        try:
            if self.provider == "openai":
                return self._understand_image_openai(image_urls, question, max_tokens)
            elif self.provider == "anthropic":
                return self._understand_image_anthropic(
                    image_urls, question, max_tokens
                )
        except Exception as e:
            logger.error(f"Vision understanding error: {e}")
            return None

    def _understand_image_openai(
        self, image_urls: list[str], question: str, max_tokens: int
    ) -> Optional[str]:
        """OpenAI GPT-4V implementation."""
        # Build image content
        content = []

        # Add images
        for url in image_urls:
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": url, "detail": "high"},
                }
            )

        # Add question
        content.append({"type": "text", "text": question})

        # Call OpenAI API
        response = self.client.ChatCompletion.create(
            model=self.model,
            messages=[{"role": "user", "content": content}],
            max_tokens=max_tokens,
        )

        return response.choices[0].message.content

    def _understand_image_anthropic(
        self, image_urls: list[str], question: str, max_tokens: int
    ) -> Optional[str]:
        """Anthropic Claude Vision implementation."""
        # Claude uses base64 content, not URLs
        # In production, fetch image from signed URL and convert to base64
        import base64

        import requests

        content = []

        for url in image_urls:
            # Fetch image from signed URL
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            image_data = base64.standard_b64encode(response.content).decode("utf-8")

            # Determine media type
            media_type = "image/jpeg"
            if url.endswith(".png"):
                media_type = "image/png"
            elif url.endswith(".webp"):
                media_type = "image/webp"
            elif url.endswith(".gif"):
                media_type = "image/gif"

            content.append(
                {
                    "type": "image",
                    "source": {"type": "base64", "media_type": media_type, "data": image_data},
                }
            )

        # Add question
        content.append({"type": "text", "text": question})

        # Call Claude API
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": content}],
        )

        return response.content[0].text

    # ============================================================================
    # Structured Extraction
    # ============================================================================

    def extract_structured_data(
        self,
        image_urls: list[str],
        extraction_type: str,
        schema: Optional[dict] = None,
        max_retries: int = 1,
    ) -> Optional[dict]:
        """
        Extract structured data from image(s).

        Args:
            image_urls: List of image URLs
            extraction_type: 'receipt', 'form', 'table', or 'custom'
            schema: For 'custom' type: {field_name: field_type}
            max_retries: Retry if JSON parsing fails

        Returns:
            Parsed data dict or None if failed
        """
        for attempt in range(max_retries + 1):
            try:
                # Build extraction prompt
                prompt = self._build_extraction_prompt(extraction_type, schema)

                # Get response
                if self.provider == "openai":
                    response_text = self._understand_image_openai(
                        image_urls, prompt, 2048
                    )
                elif self.provider == "anthropic":
                    response_text = self._understand_image_anthropic(
                        image_urls, prompt, 2048
                    )
                else:
                    return None

                if not response_text:
                    return None

                # Try to parse JSON
                try:
                    # Extract JSON from response (may be wrapped in markdown code block)
                    if "```json" in response_text:
                        json_str = response_text.split("```json")[1].split("```")[0]
                    elif "```" in response_text:
                        json_str = response_text.split("```")[1].split("```")[0]
                    else:
                        json_str = response_text

                    return json.loads(json_str.strip())

                except json.JSONDecodeError as e:
                    logger.warning(f"JSON parse attempt {attempt + 1} failed: {e}")
                    if attempt < max_retries:
                        continue
                    else:
                        return None

            except Exception as e:
                logger.error(f"Extraction error: {e}")
                if attempt < max_retries:
                    continue
                else:
                    return None

    def _build_extraction_prompt(
        self, extraction_type: str, schema: Optional[dict] = None
    ) -> str:
        """Build extraction prompt based on type."""
        if extraction_type == "receipt":
            return """Extract all line items and totals from this receipt. Return JSON:
{
  "items": [
    {"name": "...", "quantity": 1, "unit_price": 0.00, "total": 0.00}
  ],
  "subtotal": 0.00,
  "tax": 0.00,
  "total": 0.00,
  "date": "YYYY-MM-DD",
  "merchant": "..."
}"""

        elif extraction_type == "form":
            return """Extract all form fields and their values. Return JSON:
{
  "fields": {
    "field_name": "field_value",
    ...
  }
}"""

        elif extraction_type == "table":
            return """Extract table data. Return JSON:
{
  "headers": ["col1", "col2", ...],
  "rows": [
    ["val1", "val2", ...],
    ...
  ]
}"""

        elif extraction_type == "custom" and schema:
            # Build prompt for custom schema
            fields_desc = ", ".join(
                f"{name} ({type_})" for name, type_ in schema.items()
            )
            return f"""Extract the following fields from the image: {fields_desc}
Return valid JSON matching this structure:
{{
{chr(10).join(f'  "{name}": <{type_}>' for name, type_ in schema.items())}
}}"""

        else:
            return "Extract relevant information from this image as JSON."


# ============================================================================
# Global Instance
# ============================================================================

_vision_service: Optional[VisionLLMService] = None


def get_vision_service() -> VisionLLMService:
    """Get or create global vision service instance."""
    global _vision_service

    if _vision_service is None:
        _vision_service = VisionLLMService()

    return _vision_service


def set_vision_service(service: VisionLLMService) -> None:
    """Set custom vision service (for testing)."""
    global _vision_service
    _vision_service = service
