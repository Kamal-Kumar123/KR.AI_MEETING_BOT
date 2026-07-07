import json
import os
import uuid
from datetime import datetime

from config import FRONTEND_URL, HISTORY_FILE

from rag import get_rag_service


def load_meeting_history() -> list:
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []


def save_meeting_history(history: list) -> None:
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)


def generate_meeting_id() -> str:
    return uuid.uuid4().hex[:12]


def build_share_url(meeting_id: str) -> str:
    base = FRONTEND_URL.rstrip("/")
    return f"{base}/?meeting_id={meeting_id}"


def save_meeting_record(transcript, summary, action_items, mode, series_id, use_rag, source="upload"):
    meeting_id = generate_meeting_id()
    timestamp = datetime.now().isoformat()
    record = {
        "meeting_id": meeting_id,
        "timestamp": timestamp,
        "mode": mode,
        "series_id": series_id,
        "use_rag": use_rag,
        "source": source,
        "transcript": transcript,
        "summary": summary,
        "action_items": action_items,
        "share_url": build_share_url(meeting_id),
    }
    history = load_meeting_history()
    history.append(record)
    save_meeting_history(history)

    rag = get_rag_service()
    rag.index_meeting(
        meeting_id=meeting_id,
        transcript=transcript,
        summary=summary,
        action_items=action_items,
        timestamp=timestamp,
        mode=mode,
        series_id=series_id,
    )
    return meeting_id


def get_meeting_by_id(meeting_id: str) -> dict | None:
    for item in reversed(load_meeting_history()):
        if item.get("meeting_id") == meeting_id:
            return item
        if item.get("timestamp") == meeting_id:
            return item
    return None
