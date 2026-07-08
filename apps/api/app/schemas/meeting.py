from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, model_validator


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class GoogleLoginRequest(BaseModel):
    id_token: str | None = None
    access_token: str | None = None
    platform: str = Field(default="web", description="'web' for website, 'extension' for Chrome extension")

    @model_validator(mode="after")
    def require_one_token(self):
        if not self.id_token and not self.access_token:
            raise ValueError("id_token or access_token is required")
        if self.platform not in ("web", "extension"):
            raise ValueError("platform must be 'web' or 'extension'")
        return self


class ActionItemResponse(BaseModel):
    id: str
    task: str
    owner: str
    deadline: str
    status: str


class ParticipantResponse(BaseModel):
    id: str
    name: str
    email: Optional[str] = None


class TranscriptSegment(BaseModel):
    start: float = 0.0
    end: float = 0.0
    text: str = ""
    speaker: Optional[str] = None


class SummaryResponse(BaseModel):
    executive_summary: str
    detailed_summary: str
    bullet_summary: list[str]
    key_decisions: list[str]
    discussion_points: list[str]
    open_questions: list[str]
    risks: list[str]
    next_steps: list[str]
    keywords: list[str]


class MeetingResponse(BaseModel):
    id: str
    title: str
    platform: str
    status: str
    progress_message: Optional[str] = None
    duration_seconds: Optional[int] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    recording_date: Optional[datetime] = None
    tags: list[str] = []
    is_favorite: bool = False
    share_token: Optional[str] = None
    error_message: Optional[str] = None
    transcript: Optional[str] = None
    transcript_segments: list[TranscriptSegment] = []
    summary: Optional[SummaryResponse] = None
    action_items: list[ActionItemResponse] = []
    participants: list[ParticipantResponse] = []
    meeting_mode: Optional[str] = None
    series_id: Optional[str] = None
    use_rag: bool = False
    rag_context_used: bool = False


class ConfigureMeetingRequest(BaseModel):
    mode: str = Field(description="'standalone' or 'connected'")
    series_id: Optional[str] = Field(default=None, description="Required when mode is connected")
    title: Optional[str] = Field(default=None, max_length=500, description="Display name for standalone meetings")


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: Optional[str] = None


class SeriesItem(BaseModel):
    series_id: str
    meeting_count: int


class SeriesListResponse(BaseModel):
    items: list[SeriesItem]
    total: int


class MeetingListResponse(BaseModel):
    items: list[MeetingResponse]
    total: int


class CreateMeetingRequest(BaseModel):
    platform: str = "unknown"
    meeting_url: Optional[str] = None
    title: Optional[str] = None


class RecordingUploadResponse(BaseModel):
    meeting_id: str
    recording_id: str
    status: str
    message: str
    share_token: str


class GenerateSummaryRequest(BaseModel):
    meeting_id: str


class MeetingUpdateRequest(BaseModel):
    title: Optional[str] = None
    tags: Optional[list[str]] = None
    is_favorite: Optional[bool] = None
