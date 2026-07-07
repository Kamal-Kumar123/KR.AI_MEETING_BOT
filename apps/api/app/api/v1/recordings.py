from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.models import Meeting, Recording, User, get_db
from app.schemas.meeting import RecordingUploadResponse
from app.services.storage import storage_service
from app.worker.tasks import enqueue_meeting_pipeline

router = APIRouter(prefix="/recordings", tags=["recordings"])


@router.post("/upload", response_model=RecordingUploadResponse)
async def upload_recording(
    file: UploadFile = File(...),
    meeting_id: str | None = Form(default=None),
    platform: str = Form(default="unknown"),
    meeting_url: str | None = Form(default=None),
    duration_seconds: int | None = Form(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    meeting: Meeting | None = None
    if meeting_id:
        meeting = db.query(Meeting).filter(Meeting.id == meeting_id, Meeting.user_id == user.id).first()
        if not meeting:
            raise HTTPException(status_code=404, detail="Meeting not found")

    if not meeting:
        meeting = Meeting(
            user_id=user.id,
            platform=platform,
            meeting_url=meeting_url,
            status="uploading",
            progress_message="Uploading recording...",
            started_at=datetime.utcnow(),
            duration_seconds=duration_seconds,
        )
        db.add(meeting)
        db.commit()
        db.refresh(meeting)
    else:
        meeting.status = "uploading"
        meeting.progress_message = "Uploading recording..."
        db.commit()

    content = await file.read()
    ext = (file.filename or "recording.webm").split(".")[-1]
    s3_key = f"users/{user.id}/meetings/{meeting.id}/recording.{ext}"
    mime = file.content_type or "audio/webm"

    storage_service.upload_bytes(s3_key, content, mime)

    if meeting.recording:
        meeting.recording.s3_key = s3_key
        meeting.recording.mime_type = mime
        meeting.recording.size_bytes = len(content)
        meeting.recording.status = "uploaded"
    else:
        db.add(
            Recording(
                meeting_id=meeting.id,
                s3_key=s3_key,
                mime_type=mime,
                size_bytes=len(content),
                status="uploaded",
            )
        )

    meeting.status = "transcribing"
    meeting.progress_message = "Upload complete. Starting transcription..."
    meeting.ended_at = datetime.utcnow()
    db.commit()
    db.refresh(meeting)

    task_id = enqueue_meeting_pipeline(meeting.id)

    return RecordingUploadResponse(
        meeting_id=meeting.id,
        recording_id=meeting.id,
        status=meeting.status,
        message=f"Upload successful. Processing started (task: {task_id}).",
        share_token=meeting.share_token,
    )
