import os

from config import WHISPER_DEVICE, WHISPER_MODEL
from .diarization import apply_diarization, is_diarization_available

_whisper_model = None

SUPPORTED_AUDIO_EXTENSIONS = {"mp3", "wav", "m4a", "mp4", "webm", "ogg", "aac", "flac"}


def get_whisper_model():
    global _whisper_model
    if _whisper_model is None:
        from faster_whisper import WhisperModel

        compute_type = "int8" if WHISPER_DEVICE == "cpu" else "float16"
        _whisper_model = WhisperModel(WHISPER_MODEL, device=WHISPER_DEVICE, compute_type=compute_type)
    return _whisper_model


def transcribe_audio_file(file_path: str) -> dict:
    """
    Free local transcription via faster-whisper.
    Optional speaker diarization via pyannote (needs HF_TOKEN).
    """
    model = get_whisper_model()
    segments, info = model.transcribe(
        file_path,
        beam_size=5,
        vad_filter=True,
        language="en",
    )

    segment_list = []
    for segment in segments:
        text = segment.text.strip()
        if not text:
            continue
        segment_list.append(
            {
                "start": round(segment.start, 2),
                "end": round(segment.end, 2),
                "text": text,
            }
        )

    diarization = apply_diarization(file_path, segment_list)
    final_segments = diarization["segments"]
    final_text = diarization["text"] if diarization["enabled"] else "\n".join(s["text"] for s in segment_list)

    return {
        "text": final_text,
        "segments": final_segments,
        "language": info.language,
        "duration_seconds": round(info.duration, 2) if info.duration else None,
        "engine": "faster-whisper",
        "model": WHISPER_MODEL,
        "cost": "free",
        "diarization": {
            "enabled": diarization["enabled"],
            "speaker_count": diarization["speaker_count"],
            "engine": diarization.get("engine"),
            "error": diarization.get("error"),
        },
    }


def is_whisper_ready() -> bool:
    try:
        get_whisper_model()
        return True
    except Exception as exc:
        print(f"Whisper not ready: {exc}")
        return False
