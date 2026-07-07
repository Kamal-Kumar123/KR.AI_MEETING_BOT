import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _auth_headers():
    email = "phase2@example.com"
    password = "password123"
    client.post("/api/v1/auth/register", json={"email": email, "password": password})
    token = client.post("/api/v1/auth/login", json={"email": email, "password": password}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_analytics_requires_auth():
    assert client.get("/api/v1/analytics").status_code == 401


def test_analytics():
    headers = _auth_headers()
    res = client.get("/api/v1/analytics", headers=headers)
    assert res.status_code == 200
    assert "total_meetings" in res.json()


def test_settings_crud():
    headers = _auth_headers()

    settings = client.get("/api/v1/settings", headers=headers).json()
    assert settings["auto_upload"] is True

    patch = client.patch(
        "/api/v1/settings",
        headers=headers,
        json={"recording_quality": "high", "notifications": False},
    )
    assert patch.status_code == 200
    assert patch.json()["recording_quality"] == "high"
    assert patch.json()["notifications"] is False


def test_create_meeting_and_list():
    headers = _auth_headers()
    created = client.post(
        "/api/v1/meetings",
        headers=headers,
        json={"platform": "google_meet", "title": "Sprint Review"},
    )
    assert created.status_code == 200
    meeting_id = created.json()["id"]

    listed = client.get("/api/v1/meetings", headers=headers)
    assert listed.status_code == 200
    assert any(m["id"] == meeting_id for m in listed.json()["items"])
