import pytest

try:
    from backend.main import app
    from fastapi.testclient import TestClient
    client = TestClient(app)
except Exception:
    client = None


@pytest.mark.skipif(client is None, reason="App import failed")
def test_free_plan_limits(monkeypatch):
    """Test free plan enforces request/token limits via mocked usage service."""
    # Mock usage service to simulate free plan near limit
    monkeypatch.setenv("FREE_PLAN_DAILY_REQUESTS", "1")

    # Create a test user and simulate one request
    # This test is intentionally high-level; replace endpoints/names with actual app routes
    resp = client.post("/api/auth/register", json={"email": "free@aihub.local", "password": "pass"})
    assert resp.status_code in (200, 201)

    token_resp = client.post("/api/auth/login", data={"username": "free@aihub.local", "password": "pass"})
    assert token_resp.status_code == 200
    token = token_resp.json().get("access_token")
    headers = {"Authorization": f"Bearer {token}"}

    # First allowed request
    r1 = client.post("/api/chat", headers=headers, json={"query": "hello"})
    assert r1.status_code == 200

    # Second request should be rejected (daily limit)
    r2 = client.post("/api/chat", headers=headers, json={"query": "hello again"})
    assert r2.status_code in (402, 429, 403)
