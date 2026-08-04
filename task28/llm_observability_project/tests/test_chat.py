from fastapi.testclient import TestClient
from unittest.mock import patch
from app.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_chat_mocked_llm():
    fake_result = {
        "response": "RAG combines retrieval with generation.",
        "input_tokens": 10,
        "output_tokens": 8,
        "total_tokens": 18,
        "latency_ms": 120.5,
        "status": "success",
        "error": None,
    }
    with patch("app.api.chat.llm_service.call_llm", return_value=fake_result):
        r = client.post("/chat", json={
            "message": "Explain RAG",
            "use_cache": False,
            "optimize_prompt": False,
        })
        assert r.status_code == 200
        body = r.json()
        assert body["total_tokens"] == 18
        assert body["cache_hit"] is False


def test_chat_rejects_empty_message():
    r = client.post("/chat", json={"message": "", "use_cache": True, "optimize_prompt": True})
    assert r.status_code == 422
