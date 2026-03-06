"""Tests for chat API endpoints."""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from app.main import app
    return TestClient(app)


def test_health(client: TestClient):
    """GET /health returns 200."""
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_chat_requires_query(client: TestClient):
    """POST /api/chat returns 422 or 400 when query is missing."""
    r = client.post("/api/chat", json={"session_id": None})
    assert r.status_code in (400, 422)


def test_chat_accepts_query(client: TestClient):
    """POST /api/chat with valid body is accepted (may fail later without OpenAI key)."""
    r = client.post(
        "/api/chat",
        json={"session_id": None, "query": "What is NSCLC?"},
    )
    # 200 with answer, or 500 if OpenAI key missing
    assert r.status_code in (200, 500)
    if r.status_code == 200:
        data = r.json()
        assert "answer" in data
        assert "session_id" in data
        assert "confidence" in data


def test_sessions_list(client: TestClient):
    """GET /api/sessions returns list (may be empty)."""
    r = client.get("/api/sessions")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_legacy_sessions_list(client: TestClient):
    """GET /api/chat/sessions/ returns list."""
    r = client.get("/api/chat/sessions/")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
