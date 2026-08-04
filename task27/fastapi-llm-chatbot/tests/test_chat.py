from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app
from app.services.llm_service import (
    LLMNotConfiguredError,
    LLMProviderError,
    LLMRateLimitError,
    LLMTimeoutError,
)

client = TestClient(app)


def test_chat_success():
    with patch(
        "app.api.chat.LLMService.get_response",
        new=AsyncMock(return_value="Hello there!"),
    ):
        resp = client.post("/chat", json={"message": "Hi"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["response"] == "Hello there!"
    assert "model" in body
    assert "provider" in body


def test_chat_empty_message_rejected():
    resp = client.post("/chat", json={"message": ""})
    assert resp.status_code == 422


def test_chat_missing_field_rejected():
    resp = client.post("/chat", json={})
    assert resp.status_code == 422


def test_chat_not_configured():
    with patch(
        "app.api.chat.LLMService.get_response",
        new=AsyncMock(side_effect=LLMNotConfiguredError()),
    ):
        resp = client.post("/chat", json={"message": "Hi"})
    assert resp.status_code == 503


def test_chat_timeout():
    with patch(
        "app.api.chat.LLMService.get_response",
        new=AsyncMock(side_effect=LLMTimeoutError()),
    ):
        resp = client.post("/chat", json={"message": "Hi"})
    assert resp.status_code == 504


def test_chat_rate_limited():
    with patch(
        "app.api.chat.LLMService.get_response",
        new=AsyncMock(side_effect=LLMRateLimitError()),
    ):
        resp = client.post("/chat", json={"message": "Hi"})
    assert resp.status_code == 503


def test_chat_provider_error():
    with patch(
        "app.api.chat.LLMService.get_response",
        new=AsyncMock(side_effect=LLMProviderError()),
    ):
        resp = client.post("/chat", json={"message": "Hi"})
    assert resp.status_code == 502


def test_chat_message_too_long():
    with patch(
        "app.api.chat.LLMService.get_response",
        new=AsyncMock(return_value="ok"),
    ):
        resp = client.post("/chat", json={"message": "x" * 5000})
    assert resp.status_code == 400
