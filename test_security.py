from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app


def test_auth_gate_when_enabled(monkeypatch):
    monkeypatch.setattr(settings, "api_auth_enabled", True)
    monkeypatch.setattr(settings, "api_key", "secret")
    client = TestClient(app)
    try:
        assert client.get("/health").status_code == 200
        assert client.post("/analyses", json={"name": "blocked"}).status_code == 401
    finally:
        monkeypatch.setattr(settings, "api_auth_enabled", False)
        monkeypatch.setattr(settings, "api_key", None)
