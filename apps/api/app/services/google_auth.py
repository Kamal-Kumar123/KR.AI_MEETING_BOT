import requests
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

from app.core.config import settings


def _google_client_ids() -> list[str]:
    ids = []
    if settings.google_client_id:
        ids.append(settings.google_client_id)
    if settings.google_extension_client_id and settings.google_extension_client_id not in ids:
        ids.append(settings.google_extension_client_id)
    return ids


def _client_id_for_platform(platform: str) -> str:
    if platform == "extension":
        cid = settings.google_extension_client_id or settings.google_client_id
    else:
        cid = settings.google_client_id
    if not cid:
        raise ValueError("Google OAuth is not configured for this platform")
    return cid


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


def verify_google_id_token(token: str, platform: str = "web") -> dict:
    client_id = _client_id_for_platform(platform)
    payload = id_token.verify_oauth2_token(token, google_requests.Request(), client_id)
    return _normalize_google_profile(payload)


def verify_google_access_token(token: str, platform: str = "extension") -> dict:
    """Verify access tokens from chrome.identity.getAuthToken (Chrome extension flow)."""
    allowed = _google_client_ids()
    if not allowed:
        raise ValueError("Google OAuth is not configured")

    resp = requests.get(
        "https://oauth2.googleapis.com/tokeninfo",
        params={"access_token": token},
        timeout=10,
    )
    if resp.status_code != 200:
        raise ValueError("Invalid Google access token")

    payload = resp.json()
    client_id = payload.get("azp") or payload.get("aud")
    if client_id not in allowed:
        raise ValueError("Google token client mismatch")
    if platform == "web" and client_id != _client_id_for_platform(platform):
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
