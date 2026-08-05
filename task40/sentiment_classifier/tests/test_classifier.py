"""
Tests for classifier.py — uses a mocked OpenAI client so no real API key
or network call is needed to verify the logic.
"""

import pytest
from unittest.mock import MagicMock
from classifier import classify_review, classify_reviews, ClassificationError, _normalize_label


def make_mock_client(reply_text: str):
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content=reply_text))]
    mock_client.chat.completions.create.return_value = mock_response
    return mock_client


def test_classify_review_positive():
    client = make_mock_client("Positive")
    result = classify_review(client, "I love this product!")
    assert result == "Positive"


def test_classify_review_handles_lowercase_and_punctuation():
    client = make_mock_client("negative.")
    result = classify_review(client, "This is terrible.")
    assert result == "Negative"


def test_classify_review_empty_text_raises():
    client = make_mock_client("Positive")
    with pytest.raises(ClassificationError):
        classify_review(client, "")


def test_classify_review_unrecognized_label_raises():
    client = make_mock_client("Somewhat mixed feelings")
    with pytest.raises(ClassificationError):
        classify_review(client, "It was okay I guess")


def test_classify_review_wraps_api_errors():
    client = MagicMock()
    client.chat.completions.create.side_effect = Exception("network down")
    with pytest.raises(ClassificationError):
        classify_review(client, "Great product")


def test_normalize_label_variants():
    assert _normalize_label("POSITIVE") == "Positive"
    assert _normalize_label("negative.") == "Negative"
    assert _normalize_label("Neutral") == "Neutral"


def test_classify_reviews_returns_one_result_per_review():
    client = make_mock_client("Positive")
    reviews = ["Great!", "Amazing!", "Loved it!"]
    results = classify_reviews(client, reviews)
    assert len(results) == 3
    assert all(r["sentiment"] == "Positive" for r in results)


def test_classify_reviews_captures_per_review_errors():
    client = MagicMock()
    client.chat.completions.create.side_effect = Exception("boom")
    results = classify_reviews(client, ["Some review"])
    assert results[0]["sentiment"] == "ERROR"
    assert results[0]["error"] is not None
