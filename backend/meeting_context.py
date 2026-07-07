from datetime import datetime
from typing import Literal

MeetingMode = Literal["standalone", "connected"]


def normalize_meeting_context(mode: str, series_id: str | None) -> tuple[MeetingMode, str, bool]:
    """
    Returns (mode, series_id, use_rag).

    - standalone: process current meeting only; store in an isolated series scope
    - connected: retrieve past context from the same series_id before generating output
    """
    normalized_mode = (mode or "standalone").lower().strip()
    if normalized_mode not in ("standalone", "connected"):
        raise ValueError("mode must be 'standalone' or 'connected'")

    cleaned_series_id = (series_id or "").strip()

    if normalized_mode == "connected":
        if not cleaned_series_id:
            raise ValueError("series_id is required when mode is 'connected'")
        return normalized_mode, cleaned_series_id, True

    isolated_series_id = cleaned_series_id or f"standalone-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
    return normalized_mode, isolated_series_id, False
