from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_metrics_endpoint_returns_prometheus_format():
    # Hit another endpoint first so at least one metric has data.
    client.get("/health")

    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert "text/plain" in resp.headers["content-type"]
    assert "http_requests_total" in resp.text


def test_metrics_does_not_expose_secrets():
    resp = client.get("/metrics")
    text = resp.text.lower()
    assert "api_key" not in text
    assert "authorization" not in text
