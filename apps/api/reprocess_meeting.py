"""One-off utility: re-run the full AI pipeline for an existing meeting.

Usage:
    python reprocess_meeting.py <meeting_id>

Re-transcribes the stored recording with the current WHISPER_MODEL and re-runs
diarization + summary + insights with the latest prompts. Useful after changing
models/prompts without needing to record again.
"""
import sys

from app.db.models import SessionLocal
from app.services.ai_pipeline import process_meeting_pipeline


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python reprocess_meeting.py <meeting_id>")
        sys.exit(1)
    meeting_id = sys.argv[1]
    db = SessionLocal()
    try:
        print(f"Reprocessing meeting {meeting_id} ...")
        process_meeting_pipeline(db, meeting_id)
        print("REPROCESS DONE")
    finally:
        db.close()


if __name__ == "__main__":
    main()
