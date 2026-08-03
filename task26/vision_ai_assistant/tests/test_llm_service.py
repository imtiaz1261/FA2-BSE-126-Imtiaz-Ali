"""Tests for the LLM service streaming helper."""

from config.settings import get_settings
from services.llm_service import LLMService


def test_stream_chunks_preserves_word_order() -> None:
    """The streaming helper should preserve the original text order."""
    service = LLMService(get_settings())
    chunks = list(service.stream_chunks("Hello secure world"))

    assert chunks == ["Hello ", "secure ", "world"]


def test_stream_chunks_returns_empty_iterable_for_empty_text() -> None:
    """Empty text should not produce any chunks."""
    service = LLMService(get_settings())
    chunks = list(service.stream_chunks(""))

    assert chunks == []
