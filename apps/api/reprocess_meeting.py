"""One-off utility: re-run the AI pipeline for an existing meeting.

Usage:
    python reprocess_meeting.py <meeting_id>

Re-transcribes when needed, or re-runs summary + action items for meetings that
already have a transcript and meeting mode configured.
"""
import sys

from app.db.models import Meeting, SessionLocal
from app.services.ai_pipeline import finalize_meeting_insights, process_meeting_pipeline


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python reprocess_meeting.py <meeting_id>")
        sys.exit(1)
    meeting_id = sys.argv[1]
    db = SessionLocal()
    try:
        meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
        if not meeting:
            print(f"Meeting not found: {meeting_id}")
            sys.exit(1)

        print(f"Reprocessing meeting {meeting_id} ...")
        if meeting.recording and (not meeting.transcript or meeting.status == "failed"):
            process_meeting_pipeline(db, meeting_id)
            db.refresh(meeting)

        if meeting.transcript and meeting.meeting_mode:
            print("Re-running AI insights (summary + action items)...")
            finalize_meeting_insights(db, meeting_id)
        elif meeting.status == "awaiting_config":
            print("Meeting awaiting config — configure standalone/connected first.")
        else:
            print("No transcript or meeting mode — run full pipeline or configure meeting.")

        print("REPROCESS DONE")
    finally:
        db.close()


if __name__ == "__main__":
    main()
