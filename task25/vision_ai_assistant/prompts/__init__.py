"""prompts package — all LLM prompt templates and builders."""

from prompts.system_prompts import (
    SYSTEM_PROMPT_MAIN,
    SYSTEM_PROMPT_JSON_EXTRACTION,
    SYSTEM_PROMPT_QA,
    SYSTEM_PROMPT_CLASSIFY,
    get_system_prompt,
)
from prompts.extraction_prompts import (
    EXTRACTION_PROMPT_MAP,
    get_extraction_prompt,
)
from prompts.analysis_prompts import (
    INITIAL_ANALYSIS_PROMPT,
    OCR_FULL_TEXT_PROMPT,
    SUMMARY_PROMPT,
    build_question_prompt,
    get_suggestions_for_document,
    DOCUMENT_TYPE_SUGGESTIONS,
)
from prompts.templates import PromptBuilder

__all__ = [
    # system
    "SYSTEM_PROMPT_MAIN",
    "SYSTEM_PROMPT_JSON_EXTRACTION",
    "SYSTEM_PROMPT_QA",
    "SYSTEM_PROMPT_CLASSIFY",
    "get_system_prompt",
    # extraction
    "EXTRACTION_PROMPT_MAP",
    "get_extraction_prompt",
    # analysis
    "INITIAL_ANALYSIS_PROMPT",
    "OCR_FULL_TEXT_PROMPT",
    "SUMMARY_PROMPT",
    "build_question_prompt",
    "get_suggestions_for_document",
    "DOCUMENT_TYPE_SUGGESTIONS",
    # builder
    "PromptBuilder",
]
