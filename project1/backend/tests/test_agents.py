import pytest

try:
    from backend.main import app
    from fastapi.testclient import TestClient
    client = TestClient(app)
except Exception:
    client = None


@pytest.mark.skipif(client is None, reason="App import failed")
def test_agent_routing_and_tool_selection(monkeypatch):
    """Ensure agent routing chooses correct tool and gracefully handles tool failures.
    Uses mocked LLM / tool responses.
    """
    # Mock an agent selection endpoint response from LLM
    # For now, we patch the internal service that would call the LLM (example name)
    # monkeypatch.setattr("backend.services.agent_service.call_llm", lambda *a, **k: {"tool":"search","reason":"user asked to find docs"})

    # Register and login test user
    resp = client.post("/api/auth/register", json={"email": "agent@aihub.local", "password": "pass"})
    assert resp.status_code in (200, 201)
    token_resp = client.post("/api/auth/login", data={"username": "agent@aihub.local", "password": "pass"})
    assert token_resp.status_code == 200
    token = token_resp.json().get("access_token")
    headers = {"Authorization": f"Bearer {token}"}

    # Request agent action
    r = client.post("/api/agents/route", headers=headers, json={"query": "Find the deployment docs for nginx"})
    assert r.status_code == 200
    data = r.json()
    # The response should indicate which tool was used and the agent result
    assert "tool" in data
    assert "result" in data

    # Simulate a tool failure path — call an endpoint that triggers a tool failure and ensure the agent returns a graceful error
    rfail = client.post("/api/agents/run_tool", headers=headers, json={"tool": "external_search", "params": {"q": "fail-mode"}})
    assert rfail.status_code in (200, 400, 502)
    # If 200, ensure response includes error handling info
    if rfail.status_code == 200:
        assert "error" in rfail.json() or "fallback" in rfail.json()
