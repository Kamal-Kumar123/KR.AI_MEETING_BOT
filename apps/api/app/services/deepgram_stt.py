"""Cloud speech-to-text via Deepgram (replaces local faster-whisper)."""
from __future__ import annotations

import os
import tempfile

import httpx

from app.core.config import settings
from app.services.storage import storage_service

MIME_BY_EXT = {
    "wav": "audio/wav",
    "webm": "audio/webm",
    "mp3": "audio/mpeg",
    "mp4": "video/mp4",
    "m4a": "audio/mp4",
    "ogg": "audio/ogg",
    "flac": "audio/flac",
    "aac": "audio/aac",
}


def deepgram_configured() -> bool:
    return bool(settings.deepgram_api_key.strip())


def download_to_temp(s3_key: str) -> str:
    data = storage_service.download_bytes(s3_key)
    ext = s3_key.rsplit(".", 1)[-1].lower() if "." in s3_key else "webm"
    suffix = f".{ext}" if ext else ".webm"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(data)
        return tmp.name


def _mime_for_path(path: str) -> str:
    ext = path.rsplit(".", 1)[-1].lower() if "." in path else "wav"
    return MIME_BY_EXT.get(ext, "application/octet-stream")


def transcribe_audio_file(path: str) -> dict:
    if not deepgram_configured():
        raise RuntimeError("DEEPGRAM_API_KEY is not configured")

    with open(path, "rb") as audio_file:
        audio_bytes = audio_file.read()

    params = {
        "model": settings.deepgram_model,
        "smart_format": "true",
        "punctuate": "true",
        "diarize": "true",
        "utterances": "true",
    }

    with httpx.Client(timeout=600.0) as client:
        response = client.post(
            "https://api.deepgram.com/v1/listen",
            params=params,
            headers={
                "Authorization": f"Token {settings.deepgram_api_key}",
                "Content-Type": _mime_for_path(path),
            },
            content=audio_bytes,
        )
        response.raise_for_status()
        payload = response.json()

    results = payload.get("results") or {}
    channels = results.get("channels") or []
    transcript = ""
    if channels:
        alts = channels[0].get("alternatives") or []
        if alts:
            transcript = (alts[0].get("transcript") or "").strip()

    utterances = results.get("utterances") or []
    segments: list[dict] = []
    speakers_seen: set[int] = set()

    for utt in utterances:
        text = (utt.get("transcript") or "").strip()
        if not text:
            continue
        speaker_idx = int(utt.get("speaker", 0))
        speakers_seen.add(speaker_idx)
        segments.append(
            {
                "start": float(utt.get("start") or 0.0),
                "end": float(utt.get("end") or 0.0),
                "text": text,
                "speaker": f"Speaker {speaker_idx + 1}",
            }
        )

    if not segments and transcript:
        segments = [{"start": 0.0, "end": 0.0, "text": transcript}]

    metadata = payload.get("metadata") or {}
    duration = float(metadata.get("duration") or 0.0)
    if not duration and segments:
        duration = max(float(s.get("end") or 0.0) for s in segments)

    return {
        "text": transcript or " ".join(s["text"] for s in segments).strip(),
        "segments": segments,
        "duration": duration,
        "language": "en",
        "num_speakers": max(len(speakers_seen), 1) if speakers_seen else 1,
    }


def transcribe_recording(s3_key: str) -> dict:
    path = download_to_temp(s3_key)
    try:
        return transcribe_audio_file(path)
    finally:
        if os.path.exists(path):
            os.remove(path)
