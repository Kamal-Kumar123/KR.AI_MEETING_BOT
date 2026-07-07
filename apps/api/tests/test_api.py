import time

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_register_and_login():
    email = f"test{int(time.time())}@example.com"
    password = "password123"
    reg = client.post("/api/v1/auth/register", json={"email": email, "password": password})
    assert reg.status_code == 200
    assert "access_token" in reg.json()

    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200
    token = login.json()["access_token"]

    meetings = client.get("/api/v1/meetings", headers={"Authorization": f"Bearer {token}"})
    assert meetings.status_code == 200
    assert meetings.json()["total"] >= 0


def test_upload_recording():
    email = f"upload{int(time.time())}@example.com"
    password = "password123"
    token = client.post("/api/v1/auth/register", json={"email": email, "password": password}).json()[
        "access_token"
    ]
    headers = {"Authorization": f"Bearer {token}"}

    meeting = client.post(
        "/api/v1/meetings",
        headers=headers,
        json={"platform": "google_meet", "title": "Upload test"},
    )
    assert meeting.status_code == 200
    meeting_id = meeting.json()["id"]

    fake_audio = b"RIFF" + b"\x00" * 100
    res = client.post(
        "/api/v1/recordings/upload",
        headers=headers,
        data={"meeting_id": meeting_id, "platform": "google_meet"},
        files={"file": ("test.webm", fake_audio, "audio/webm")},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["meeting_id"] == meeting_id
    assert "Upload successful" in body["message"]
