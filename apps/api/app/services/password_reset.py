"""Password reset token creation and validation."""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import PasswordResetToken, User
from app.services.email_service import send_password_reset_email


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def create_reset_token(db: Session, user: User) -> str:
    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id,
        PasswordResetToken.used_at.is_(None),
    ).update({"used_at": _utcnow()})

    token = secrets.token_urlsafe(32)
    expires_at = _utcnow() + timedelta(minutes=settings.password_reset_expire_minutes)
    db.add(
        PasswordResetToken(
            user_id=user.id,
            token=token,
            expires_at=expires_at,
        )
    )
    db.commit()
    return token


def build_reset_url(token: str) -> str:
    base = settings.frontend_url.rstrip("/")
    return f"{base}/reset-password?token={token}"


def request_password_reset(db: Session, email: str) -> None:
    user = db.query(User).filter(func.lower(User.email) == email.strip().lower()).first()
    if not user:
        return
    if not user.password_hash:
        # Google-only account — no password to reset.
        return

    token = create_reset_token(db, user)
    reset_url = build_reset_url(token)
    send_password_reset_email(user.email, reset_url)


def reset_password_with_token(db: Session, token: str, new_password: str) -> User:
    row = db.query(PasswordResetToken).filter(PasswordResetToken.token == token).first()
    if not row or row.used_at is not None:
        raise ValueError("Invalid or expired reset link")
    if row.expires_at < _utcnow():
        raise ValueError("Reset link has expired. Request a new one.")

    user = db.query(User).filter(User.id == row.user_id).first()
    if not user:
        raise ValueError("Invalid or expired reset link")

    from app.core.security import hash_password

    user.password_hash = hash_password(new_password)
    row.used_at = _utcnow()
    db.commit()
    db.refresh(user)
    return user
