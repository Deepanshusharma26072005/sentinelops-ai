from fastapi.testclient import TestClient

from app.main import app, state

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_error_endpoint_returns_500():
    r = client.get("/error")
    assert r.status_code == 500


def test_metrics_exposed():
    client.get("/health")
    r = client.get("/metrics")
    assert r.status_code == 200
    assert "http_requests_total" in r.text


def test_break_makes_health_fail():
    state["healthy"] = True
    client.get("/break")
    assert client.get("/health").status_code == 503
    state["healthy"] = True