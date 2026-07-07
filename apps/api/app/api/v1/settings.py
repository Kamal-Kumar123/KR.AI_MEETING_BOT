from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.models import User, get_db

router = APIRouter(prefix="/settings", tags=["settings"])

DEFAULT_SETTINGS = {
    "auto_upload": True,
    "auto_summary": True,
    "open_dashboard": True,
    "dark_mode": True,
    "recording_quality": "medium",
    "language": "en-US",
    "notifications": True,
}


class UserSettingsResponse(BaseModel):
    auto_upload: bool = True
    auto_summary: bool = True
    open_dashboard: bool = True
    dark_mode: bool = True
    recording_quality: str = "medium"
    language: str = "en-US"
    notifications: bool = True


class UserSettingsUpdate(BaseModel):
    auto_upload: bool | None = None
    auto_summary: bool | None = None
    open_dashboard: bool | None = None
    dark_mode: bool | None = None
    recording_quality: Literal["low", "medium", "high"] | None = None
    language: str | None = None
    notifications: bool | None = None


@router.get("", response_model=UserSettingsResponse)
def get_settings(user: User = Depends(get_current_user)):
    merged = {**DEFAULT_SETTINGS, **(user.settings_json or {})}
    return UserSettingsResponse(**merged)


@router.patch("", response_model=UserSettingsResponse)
def update_settings(
    data: UserSettingsUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    current = {**DEFAULT_SETTINGS, **(user.settings_json or {})}
    updates = data.model_dump(exclude_unset=True)
    current.update(updates)
    user.settings_json = current
    db.commit()
    db.refresh(user)
    return UserSettingsResponse(**current)
