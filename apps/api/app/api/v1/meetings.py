from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_optional_user
from app.db.models import Meeting, User, get_db
from app.schemas.meeting import CreateMeetingRequest, GenerateSummaryRequest, MeetingListResponse, MeetingResponse, MeetingUpdateRequest
from app.services.meeting_service import get_meeting_or_404, meeting_to_response
from app.services.pdf_export import build_meeting_pdf
from app.services.storage import storage_service
from app.worker.tasks import enqueue_meeting_pipeline

router = APIRouter(tags=["meetings"])


@router.post("/meetings", response_model=MeetingResponse)
def create_meeting(
    data: CreateMeetingRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    meeting = Meeting(
        user_id=user.id,
        platform=data.platform,
        meeting_url=data.meeting_url,
        title=data.title or "Untitled Meeting",
        status="detecting",
        progress_message="Waiting for recording...",
    )
    db.add(meeting)
    db.commit()
    db.refresh(meeting)
    return meeting_to_response(meeting)


@router.get("/meetings", response_model=MeetingListResponse)
def list_meetings(
    q: str | None = Query(default=None),
    tag: str | None = Query(default=None),
    favorite: bool | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = db.query(Meeting).filter(Meeting.user_id == user.id)
    if q:
        query = query.filter(or_(Meeting.title.ilike(f"%{q}%"), Meeting.platform.ilike(f"%{q}%")))
    if tag:
        query = query.filter(Meeting.tags.contains([tag]))
    if favorite is not None:
        query = query.filter(Meeting.is_favorite == favorite)
    meetings = query.order_by(Meeting.created_at.desc()).all()
    items = [meeting_to_response(m) for m in meetings]
    return MeetingListResponse(items=items, total=len(items))


@router.get("/meeting/{meeting_id}", response_model=MeetingResponse)
def get_meeting(
    meeting_id: str,
    share: str | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User | None = Depends(get_optional_user),
):
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    if user and meeting.user_id == user.id:
        return meeting_to_response(meeting)
    if share and meeting.share_token == share:
        return meeting_to_response(meeting)
    if user and meeting.user_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    if not share:
        raise HTTPException(status_code=401, detail="Authentication or share token required")
    raise HTTPException(status_code=403, detail="Invalid share token")


@router.patch("/meeting/{meeting_id}", response_model=MeetingResponse)
def update_meeting(
    meeting_id: str,
    data: MeetingUpdateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    meeting = get_meeting_or_404(db, meeting_id, user.id)
    if data.title is not None:
        meeting.title = data.title
    if data.tags is not None:
        meeting.tags = data.tags
    if data.is_favorite is not None:
        meeting.is_favorite = data.is_favorite
    db.commit()
    db.refresh(meeting)
    return meeting_to_response(meeting)


@router.delete("/meeting/{meeting_id}")
def delete_meeting(
    meeting_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    meeting = get_meeting_or_404(db, meeting_id, user.id)
    if meeting.recording:
        try:
            storage_service.delete_object(meeting.recording.s3_key)
        except Exception:
            pass
    db.delete(meeting)
    db.commit()
    return {"message": "Meeting and recording deleted"}


@router.get("/meeting/{meeting_id}/export/pdf")
def export_meeting_pdf(
    meeting_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    meeting = get_meeting_or_404(db, meeting_id, user.id)
    if meeting.status != "ready":
        raise HTTPException(status_code=400, detail="Meeting not ready for export")
    pdf_bytes = build_meeting_pdf(meeting)
    filename = f"krai-meeting-{meeting_id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/generate-summary")
def regenerate_summary(
    data: GenerateSummaryRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    meeting = get_meeting_or_404(db, data.meeting_id, user.id)
    if not meeting.transcript:
        raise HTTPException(status_code=400, detail="Transcript required before summary generation")
    meeting.status = "processing"
    meeting.progress_message = "Regenerating insights..."
    db.commit()
    task_id = enqueue_meeting_pipeline(meeting.id)
    return {"meeting_id": meeting.id, "status": meeting.status, "task_id": task_id}


@router.post("/transcribe")
def transcribe_meeting(
    data: GenerateSummaryRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    meeting = get_meeting_or_404(db, data.meeting_id, user.id)
    if not meeting.recording:
        raise HTTPException(status_code=400, detail="Recording not found")
    meeting.status = "transcribing"
    db.commit()
    task_id = enqueue_meeting_pipeline(meeting.id)
    return {"meeting_id": meeting.id, "status": meeting.status, "task_id": task_id}
