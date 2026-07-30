from fastapi.testclient import TestClient

from app.api.server import create_app


def test_health_returns_up():
    client = TestClient(create_app())
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "UP"}
