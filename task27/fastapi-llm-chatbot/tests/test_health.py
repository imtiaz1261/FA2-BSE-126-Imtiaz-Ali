from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root():
    resp = client.get("/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "running"
    assert "application" in body
    assert "version" in body


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "healthy"}


def test_ready():
    resp = client.get("/ready")
    assert resp.status_code == 200
    body = resp.json()
    assert "status" in body
    assert "llm_configured" in body
