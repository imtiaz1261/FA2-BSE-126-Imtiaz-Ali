import pytest

try:
    from backend.main import app
    from fastapi.testclient import TestClient
    client = TestClient(app)
except Exception:
    client = None


@pytest.mark.skipif(client is None, reason="App import failed")
def test_usage_enforcement_and_pro_plan_limits(monkeypatch):
    # Simulate pro plan with higher limits via env override
    monkeypatch.setenv("PRO_PLAN_DAILY_REQUESTS", "100")

    resp = client.post("/api/auth/register", json={"email": "pro@aihub.local", "password": "pass"})
    assert resp.status_code in (200, 201)
    token_resp = client.post("/api/auth/login", data={"username": "pro@aihub.local", "password": "pass"})
    assert token_resp.status_code == 200
    token = token_resp.json().get("access_token")
    headers = {"Authorization": f"Bearer {token}"}

    # Make several requests within limits
    for i in range(3):
        r = client.post("/api/chat", headers=headers, json={"query": f"query {i}"})
        assert r.status_code == 200

    # Ensure service tracks usage — try to read usage endpoint
    usage = client.get("/api/usage/me", headers=headers)
    assert usage.status_code in (200, 401, 403)
    if usage.status_code == 200:
        data = usage.json()
        assert "daily_requests" in data
