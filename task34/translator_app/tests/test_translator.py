"""
Tests for translator.py — uses a mocked OpenAI client so no real API key
or network call is needed to verify the logic.
"""

import pytest
from unittest.mock import MagicMock
from translator import translate, TranslationError


def make_mock_client(reply_text: str):
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content=reply_text))]
    mock_client.chat.completions.create.return_value = mock_response
    return mock_client


def test_translate_returns_stripped_text():
    client = make_mock_client("  Bonjour le monde  ")
    result = translate(client, "Hello world", "French")
    assert result == "Bonjour le monde"


def test_translate_empty_text_raises():
    client = make_mock_client("irrelevant")
    with pytest.raises(TranslationError):
        translate(client, "", "French")


def test_translate_empty_language_raises():
    client = make_mock_client("irrelevant")
    with pytest.raises(TranslationError):
        translate(client, "Hello", "")


def test_translate_wraps_api_errors():
    client = MagicMock()
    client.chat.completions.create.side_effect = Exception("network down")
    with pytest.raises(TranslationError):
        translate(client, "Hello", "Spanish")
