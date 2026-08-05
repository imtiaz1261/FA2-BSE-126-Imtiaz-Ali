"""
Tests for corrector.py — uses a mocked OpenAI client so no real API key
or network call is needed to verify the logic.
"""

import json
import pytest
from unittest.mock import MagicMock
from corrector import correct_text, _parse_response, CorrectionError


def make_mock_client(reply_text: str):
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content=reply_text))]
    mock_client.chat.completions.create.return_value = mock_response
    return mock_client


def test_correct_text_parses_valid_json():
    reply = json.dumps({
        "corrected_text": "She goes to the market every day.",
        "changes": ["Fixed subject-verb agreement"],
    })
    client = make_mock_client(reply)
    result = correct_text(client, "She go to the market every day.")
    assert result["corrected_text"] == "She goes to the market every day."
    assert result["changes"] == ["Fixed subject-verb agreement"]


def test_correct_text_empty_input_raises():
    client = make_mock_client("{}")
    with pytest.raises(CorrectionError):
        correct_text(client, "")


def test_correct_text_wraps_api_errors():
    client = MagicMock()
    client.chat.completions.create.side_effect = Exception("network down")
    with pytest.raises(CorrectionError):
        correct_text(client, "some text")


def test_parse_response_strips_markdown_fences():
    raw = '```json\n{"corrected_text": "Fixed.", "changes": []}\n```'
    result = _parse_response(raw)
    assert result["corrected_text"] == "Fixed."
    assert result["changes"] == []


def test_parse_response_missing_field_raises():
    raw = json.dumps({"changes": ["something"]})
    with pytest.raises(CorrectionError):
        _parse_response(raw)


def test_parse_response_invalid_json_raises():
    with pytest.raises(CorrectionError):
        _parse_response("not valid json at all")


def test_parse_response_coerces_non_list_changes():
    raw = json.dumps({"corrected_text": "Fixed.", "changes": "one change only"})
    result = _parse_response(raw)
    assert result["changes"] == ["one change only"]
