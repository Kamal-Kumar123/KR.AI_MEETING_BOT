from typing import Literal

MeetingMode = Literal["standalone", "connected"]


def normalize_meeting_context(mode: str, series_id: str | None) -> tuple[MeetingMode, str | None, bool]:
    """Return (mode, series_id, use_rag).

    - standalone: current meeting only; no series, no RAG
    - connected: pull past context from the same series_id before generating output
    """
    normalized_mode = (mode or "standalone").lower().strip()
    if normalized_mode not in ("standalone", "connected"):
        raise ValueError("mode must be 'standalone' or 'connected'")

    cleaned_series_id = (series_id or "").strip() or None

    if normalized_mode == "connected":
        if not cleaned_series_id:
            raise ValueError("series_id is required when mode is 'connected'")
        return normalized_mode, cleaned_series_id, True

    return normalized_mode, None, False
