from sqlalchemy.orm import Session

from app.db.models import Meeting


def _as_str_list(value) -> list[str]:
    """Coerce a stored list into a list of clean strings.

    The local LLM (Ollama) sometimes returns objects like {"task": ..., "owner":
    ...} inside fields that the API contract declares as list[str]. Flatten those
    so response serialization never fails with a validation error.
    """
    if not value:
        return []
    out: list[str] = []
    for item in value:
        if isinstance(item, str):
            text = item
        elif isinstance(item, dict):
            main = (
                item.get("task")
                or item.get("text")
                or item.get("decision")
                or item.get("point")
                or item.get("question")
                or item.get("step")
                or item.get("risk")
            )
            parts = [str(main)] if main else []
            if item.get("owner"):
                parts.append(f"- {item['owner']}")
            if item.get("deadline"):
                parts.append(f"(by {item['deadline']})")
            text = " ".join(parts) if parts else str(item)
        else:
            text = str(item)
        text = text.strip()
        if text:
            out.append(text)
    return out


def meeting_to_response(meeting: Meeting, include_transcript: bool = True) -> dict:
    transcript_text = None
    transcript_segments = []
    if include_transcript and meeting.transcript:
        transcript_text = meeting.transcript.full_text
        transcript_segments = meeting.transcript.segments_json or []

    summary = None
    if meeting.summary:
        summary = {
            "executive_summary": meeting.summary.executive_summary,
            "detailed_summary": meeting.summary.detailed_summary,
            "bullet_summary": _as_str_list(meeting.summary.bullet_summary),
            "key_decisions": _as_str_list(meeting.summary.key_decisions),
            "discussion_points": _as_str_list(meeting.summary.discussion_points),
            "open_questions": _as_str_list(meeting.summary.open_questions),
            "risks": _as_str_list(meeting.summary.risks),
            "next_steps": _as_str_list(meeting.summary.next_steps),
            "keywords": _as_str_list(meeting.summary.keywords),
        }

    return {
        "id": meeting.id,
        "title": meeting.title,
        "platform": meeting.platform,
        "status": meeting.status,
        "progress_message": meeting.progress_message,
        "duration_seconds": meeting.duration_seconds,
        "started_at": meeting.started_at,
        "ended_at": meeting.ended_at,
        "recording_date": meeting.created_at,
        "tags": meeting.tags or [],
        "is_favorite": meeting.is_favorite,
        "share_token": meeting.share_token,
        "error_message": meeting.error_message,
        "transcript": transcript_text,
        "transcript_segments": transcript_segments,
        "summary": summary,
        "action_items": [
            {
                "id": a.id,
                "task": a.task,
                "owner": a.owner,
                "deadline": a.deadline,
                "status": a.status,
            }
            for a in meeting.action_items
        ],
        "participants": [
            {"id": p.id, "name": p.name, "email": p.email}
            for p in meeting.participants
        ],
    }


def get_meeting_or_404(db: Session, meeting_id: str, user_id: str | None = None) -> Meeting:
    query = db.query(Meeting).filter(Meeting.id == meeting_id)
    if user_id:
        query = query.filter(Meeting.user_id == user_id)
    meeting = query.first()
    if not meeting:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Meeting not found")
    return meeting
