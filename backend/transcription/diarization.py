import os

from config import ENABLE_DIARIZATION, HF_TOKEN

_diarization_pipeline = None


def is_diarization_available() -> bool:
    return ENABLE_DIARIZATION and bool(HF_TOKEN)


def get_diarization_pipeline():
    global _diarization_pipeline
    if _diarization_pipeline is None:
        from pyannote.audio import Pipeline

        if not HF_TOKEN:
            raise RuntimeError("HF_TOKEN is required for diarization")

        try:
            _diarization_pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1",
                token=HF_TOKEN,
            )
        except TypeError:
            _diarization_pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1",
                use_auth_token=HF_TOKEN,
            )

    return _diarization_pipeline


def diarize_audio(file_path: str) -> list[dict]:
    pipeline = get_diarization_pipeline()
    diarization = pipeline(file_path)

    speaker_labels = {}
    turns = []
    for turn, _, speaker_id in diarization.itertracks(yield_label=True):
        if speaker_id not in speaker_labels:
            speaker_labels[speaker_id] = f"Speaker {len(speaker_labels) + 1}"
        turns.append(
            {
                "start": round(turn.start, 2),
                "end": round(turn.end, 2),
                "speaker": speaker_labels[speaker_id],
                "speaker_id": speaker_id,
            }
        )
    return turns


def _best_speaker(segment_start: float, segment_end: float, turns: list[dict]) -> str:
    best_speaker = "Unknown"
    best_overlap = 0.0
    for turn in turns:
        overlap = max(0.0, min(segment_end, turn["end"]) - max(segment_start, turn["start"]))
        if overlap > best_overlap:
            best_overlap = overlap
            best_speaker = turn["speaker"]
    return best_speaker


def label_whisper_segments(whisper_segments: list[dict], diarization_turns: list[dict]) -> list[dict]:
    labeled = []
    for segment in whisper_segments:
        speaker = _best_speaker(segment["start"], segment["end"], diarization_turns)
        labeled.append({**segment, "speaker": speaker})
    return labeled


def format_diarized_transcript(labeled_segments: list[dict]) -> str:
    if not labeled_segments:
        return ""

    lines = []
    current_speaker = None
    current_text = []

    for segment in labeled_segments:
        speaker = segment.get("speaker", "Unknown")
        text = segment.get("text", "").strip()
        if not text:
            continue

        if speaker != current_speaker:
            if current_text:
                lines.append(f"{current_speaker}: {' '.join(current_text)}")
            current_speaker = speaker
            current_text = [text]
        else:
            current_text.append(text)

    if current_text and current_speaker:
        lines.append(f"{current_speaker}: {' '.join(current_text)}")

    return "\n".join(lines)


def apply_diarization(file_path: str, whisper_segments: list[dict]) -> dict:
    if not is_diarization_available():
        return {
            "enabled": False,
            "text": None,
            "segments": whisper_segments,
            "speaker_count": 0,
            "engine": None,
        }

    try:
        turns = diarize_audio(file_path)
        labeled = label_whisper_segments(whisper_segments, turns)
        speakers = {segment["speaker"] for segment in labeled}
        return {
            "enabled": True,
            "text": format_diarized_transcript(labeled),
            "segments": labeled,
            "speaker_count": len(speakers),
            "engine": "pyannote/speaker-diarization-3.1",
            "turns": turns,
        }
    except Exception as exc:
        print(f"Diarization failed, using plain transcript: {exc}")
        return {
            "enabled": False,
            "text": None,
            "segments": whisper_segments,
            "speaker_count": 0,
            "engine": None,
            "error": str(exc),
        }
