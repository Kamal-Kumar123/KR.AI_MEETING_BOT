"""Send transactional email via EmailJS REST API."""
from __future__ import annotations

import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

EMAILJS_SEND_URL = "https://api.emailjs.com/api/v1.0/email/send"


def _send_template(template_params: dict) -> None:
    if not settings.emailjs_configured():
        raise RuntimeError(
            "EmailJS is not configured. Set EMAILJS_SERVICE_ID, EMAILJS_TEMPLATE_ID, "
            "and EMAILJS_PUBLIC_KEY on the server."
        )

    payload = {
        "service_id": settings.emailjs_service_id.strip(),
        "template_id": settings.emailjs_template_id.strip(),
        "user_id": settings.emailjs_public_key.strip(),
        "template_params": template_params,
    }
    private_key = settings.emailjs_private_key.strip()
    if private_key:
        payload["accessToken"] = private_key

    try:
        response = httpx.post(EMAILJS_SEND_URL, json=payload, timeout=30.0)
        if response.status_code >= 400:
            detail = response.text.strip() or response.reason_phrase
            logger.error("EmailJS error %s: %s", response.status_code, detail)
            raise RuntimeError(f"EmailJS send failed: {detail}")
    except httpx.HTTPError as exc:
        logger.exception("EmailJS request failed")
        raise RuntimeError(f"Could not send email: {exc}") from exc


def send_password_reset_email(to: str, reset_url: str) -> None:
    """Template must use: {{to_email}}, {{reset_url}}, {{expire_minutes}}."""
    _send_template(
        {
            "to_email": to,
            "reset_url": reset_url,
            "expire_minutes": str(settings.password_reset_expire_minutes),
        }
    )
