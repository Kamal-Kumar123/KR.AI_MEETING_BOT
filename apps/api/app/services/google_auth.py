import requests
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

from app.core.config import settings


def _ensure_client_configured() -> None:
    if not settings.google_client_id:
        raise ValueError("GOOGLE_CLIENT_ID is not configured")


def _normalize_google_profile(payload: dict) -> dict:
    email = payload.get("email")
    google_id = payload.get("sub") or payload.get("user_id")
    if not email or not google_id:
        raise ValueError("Google token missing email or sub")
    return {
        "email": email,
        "sub": google_id,
        "name": payload.get("name"),
    }


def verify_google_id_token(token: str) -> dict:
    _ensure_client_configured()
    payload = id_token.verify_oauth2_token(token, google_requests.Request(), settings.google_client_id)
    return _normalize_google_profile(payload)


def verify_google_access_token(token: str) -> dict:
    """Verify access tokens from chrome.identity.getAuthToken (Chrome extension flow)."""
    _ensure_client_configured()
    resp = requests.get(
        "https://oauth2.googleapis.com/tokeninfo",
        params={"access_token": token},
        timeout=10,
    )
    if resp.status_code != 200:
        raise ValueError("Invalid Google access token")

    payload = resp.json()
    client_id = payload.get("azp") or payload.get("aud")
    if client_id != settings.google_client_id:
        raise ValueError("Google token client mismatch")

    if not payload.get("email"):
        userinfo = requests.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        if userinfo.status_code != 200:
            raise ValueError("Could not fetch Google profile")
        payload = {**payload, **userinfo.json()}

    return _normalize_google_profile(payload)
