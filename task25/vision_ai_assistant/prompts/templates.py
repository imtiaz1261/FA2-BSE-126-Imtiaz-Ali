"""
prompts/templates.py
====================
PromptBuilder — central factory that assembles complete, ready-to-send
prompt payloads for the OpenAI Chat Completions API.

This is the only class that services/llm_service.py and
services/vision_service.py need to import from the prompts package.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from prompts.analysis_prompts import (
    INITIAL_ANALYSIS_PROMPT,
    OCR_FULL_TEXT_PROMPT,
    SUMMARY_PROMPT,
    JSON_REQUEST_PROMPT,
    TABLE_EXTRACTION_PROMPT,
    VALIDATION_PROMPT,
    build_question_prompt,
    get_suggestions_for_document,
)
from prompts.extraction_prompts import get_extraction_prompt
from prompts.system_prompts import get_system_prompt


# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------
OpenAIMessage = Dict[str, Any]   # {"role": "...", "content": [...] | "..."}


class PromptBuilder:
    """
    Stateless factory for building OpenAI-compatible message payloads.

    All methods return a list of message dicts ready to pass directly to
    openai.chat.completions.create(messages=...).
    """

    # ------------------------------------------------------------------
    # Image helper
    # ------------------------------------------------------------------
    @staticmethod
    def _image_content_block(data_uri: str) -> Dict[str, Any]:
        """Build an OpenAI vision image_url content block from a data URI."""
        return {
            "type": "image_url",
            "image_url": {
                "url": data_uri,
                "detail": "high",   # use high detail for document analysis
            },
        }

    @staticmethod
    def _text_content_block(text: str) -> Dict[str, Any]:
        """Build an OpenAI text content block."""
        return {"type": "text", "text": text}

    # ------------------------------------------------------------------
    # Document classification
    # ------------------------------------------------------------------
    @classmethod
    def classify_document(cls, data_uri: str) -> List[OpenAIMessage]:
        """
        Build messages to classify the document type.
        Returns raw JSON with document_type, confidence, language.
        """
        return [
            {
                "role": "system",
                "content": get_system_prompt("classify"),
            },
            {
                "role": "user",
                "content": [
                    cls._image_content_block(data_uri),
                    cls._text_content_block(
                        "Classify this document. Return only the JSON object as instructed."
                    ),
                ],
            },
        ]

    # ------------------------------------------------------------------
    # Initial analysis (shown immediately after upload)
    # ------------------------------------------------------------------
    @classmethod
    def initial_analysis(cls, data_uri: str) -> List[OpenAIMessage]:
        """
        Build messages for the initial document overview analysis.
        This is the first thing shown to the user after upload.
        """
        return [
            {
                "role": "system",
                "content": get_system_prompt("main"),
            },
            {
                "role": "user",
                "content": [
                    cls._image_content_block(data_uri),
                    cls._text_content_block(INITIAL_ANALYSIS_PROMPT),
                ],
            },
        ]

    # ------------------------------------------------------------------
    # Structured extraction
    # ------------------------------------------------------------------
    @classmethod
    def extract_structured(
        cls,
        data_uri: str,
        document_type: str,
    ) -> List[OpenAIMessage]:
        """
        Build messages for structured JSON extraction based on document type.
        The system prompt is set to JSON extraction mode.
        """
        extraction_prompt = get_extraction_prompt(document_type)
        return [
            {
                "role": "system",
                "content": get_system_prompt("json"),
            },
            {
                "role": "user",
                "content": [
                    cls._image_content_block(data_uri),
                    cls._text_content_block(extraction_prompt),
                ],
            },
        ]

    # ------------------------------------------------------------------
    # Q&A with full conversation history
    # ------------------------------------------------------------------
    @classmethod
    def question_with_history(
        cls,
        data_uri: str,
        question: str,
        history: List[OpenAIMessage],
        is_followup: bool = False,
    ) -> List[OpenAIMessage]:
        """
        Build messages for a Q&A turn that includes conversation history.

        On the first turn, the image is embedded in the user message.
        On follow-up turns, the image is re-sent (required by OpenAI API —
        images are not persisted across turns).

        Args:
            data_uri:   Base64 data URI of the image
            question:   User's question text
            history:    Prior conversation messages (OpenAI format)
            is_followup: True when this is not the first question

        Returns:
            Complete messages list for the API call
        """
        user_prompt = build_question_prompt(question, has_prior_context=is_followup)

        messages: List[OpenAIMessage] = [
            {
                "role": "system",
                "content": get_system_prompt("qa"),
            },
        ]

        # Add prior conversation history (text only, no images in history)
        messages.extend(history)

        # Current user turn — always includes the image
        messages.append(
            {
                "role": "user",
                "content": [
                    cls._image_content_block(data_uri),
                    cls._text_content_block(user_prompt),
                ],
            }
        )

        return messages

    # ------------------------------------------------------------------
    # OCR full text extraction
    # ------------------------------------------------------------------
    @classmethod
    def ocr_extract(cls, data_uri: str) -> List[OpenAIMessage]:
        """Build messages for full OCR text extraction."""
        return [
            {
                "role": "system",
                "content": get_system_prompt("main"),
            },
            {
                "role": "user",
                "content": [
                    cls._image_content_block(data_uri),
                    cls._text_content_block(OCR_FULL_TEXT_PROMPT),
                ],
            },
        ]

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    @classmethod
    def summarize(cls, data_uri: str) -> List[OpenAIMessage]:
        """Build messages for document summary generation."""
        return [
            {
                "role": "system",
                "content": get_system_prompt("main"),
            },
            {
                "role": "user",
                "content": [
                    cls._image_content_block(data_uri),
                    cls._text_content_block(SUMMARY_PROMPT),
                ],
            },
        ]

    # ------------------------------------------------------------------
    # JSON on-demand (user asks "give me JSON" mid-conversation)
    # ------------------------------------------------------------------
    @classmethod
    def json_on_demand(
        cls,
        data_uri: str,
        history: List[OpenAIMessage],
    ) -> List[OpenAIMessage]:
        """
        Build messages when the user explicitly requests JSON output
        mid-conversation (e.g. 'convert to JSON', 'extract as JSON').
        """
        messages: List[OpenAIMessage] = [
            {
                "role": "system",
                "content": get_system_prompt("main"),
            },
        ]
        messages.extend(history)
        messages.append(
            {
                "role": "user",
                "content": [
                    cls._image_content_block(data_uri),
                    cls._text_content_block(JSON_REQUEST_PROMPT),
                ],
            }
        )
        return messages

    # ------------------------------------------------------------------
    # Table extraction
    # ------------------------------------------------------------------
    @classmethod
    def extract_table(cls, data_uri: str) -> List[OpenAIMessage]:
        """Build messages to extract tabular data as Markdown table."""
        return [
            {
                "role": "system",
                "content": get_system_prompt("main"),
            },
            {
                "role": "user",
                "content": [
                    cls._image_content_block(data_uri),
                    cls._text_content_block(TABLE_EXTRACTION_PROMPT),
                ],
            },
        ]

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    @classmethod
    def validate_document(cls, data_uri: str) -> List[OpenAIMessage]:
        """Build messages to validate a document for completeness."""
        return [
            {
                "role": "system",
                "content": get_system_prompt("main"),
            },
            {
                "role": "user",
                "content": [
                    cls._image_content_block(data_uri),
                    cls._text_content_block(VALIDATION_PROMPT),
                ],
            },
        ]

    # ------------------------------------------------------------------
    # Utility: detect if user input is a JSON request
    # ------------------------------------------------------------------
    @staticmethod
    def is_json_request(user_input: str) -> bool:
        """
        Return True if the user's message is asking for JSON output.
        Used to decide whether to call json_on_demand vs question_with_history.
        """
        lower = user_input.lower()
        json_triggers = [
            "json", "structured", "extract all",
            "as json", "to json", "convert to",
            "give me json", "return json",
        ]
        return any(trigger in lower for trigger in json_triggers)

    # ------------------------------------------------------------------
    # Utility: suggestions
    # ------------------------------------------------------------------
    @staticmethod
    def get_suggestions(document_type: str) -> list[str]:
        """Return suggested follow-up questions for a document type."""
        return get_suggestions_for_document(document_type)
