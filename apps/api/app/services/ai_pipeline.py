import json
import os
import re
import tempfile
from datetime import datetime

import requests
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import ActionItem, Meeting, Participant, Summary, Transcript
from app.services.storage import storage_service

os.environ["TOKENIZERS_PARALLELISM"] = "false"


def _ollama_available() -> bool:
    try:
        r = requests.get(f"{settings.ollama_base_url}/api/tags", timeout=5)
        if r.status_code != 200:
            return False
        names = [m.get("name", "") for m in r.json().get("models", [])]
        return any(settings.ollama_model in n for n in names)
    except Exception:
        return False


def _ollama_chat(system: str, user: str, max_tokens: int = 1200) -> str:
    response = requests.post(
        f"{settings.ollama_base_url}/api/chat",
        json={
            "model": settings.ollama_model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "stream": False,
            "options": {"temperature": 0.2, "num_predict": max_tokens},
        },
        timeout=300,
    )
    response.raise_for_status()
    return response.json()["message"]["content"].strip()


def _get_summarizer():
    from transformers import pipeline

    return pipeline("text2text-generation", model="t5-small", device=-1)


def _t5_summarize(text: str, max_len: int = 150) -> str:
    if len(text.split()) < 20:
        return text
    summarizer = _get_summarizer()
    out = summarizer(f"summarize: {text[:3000]}", max_length=max_len, min_length=30, do_sample=False)
    return out[0]["generated_text"]


_WHISPER_MODEL = None


def _get_whisper_model():
    global _WHISPER_MODEL
    if _WHISPER_MODEL is None:
        from faster_whisper import WhisperModel

        compute = "int8" if settings.whisper_device == "cpu" else "float16"
        _WHISPER_MODEL = WhisperModel(
            settings.whisper_model,
            device=settings.whisper_device,
            compute_type=compute,
        )
    return _WHISPER_MODEL


def download_to_temp(s3_key: str) -> str:
    data = storage_service.download_bytes(s3_key)
    suffix = ".webm" if s3_key.endswith(".webm") else ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(data)
        return tmp.name


def transcribe_audio_file(path: str) -> dict:
    model = _get_whisper_model()
    # Higher accuracy: beam search + VAD to drop silence/noise that causes
    # hallucinations ("you", "thanks for watching"). word_timestamps enable
    # speaker diarization alignment downstream.
    segments, info = model.transcribe(
        path,
        beam_size=5,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 500},
        word_timestamps=True,
        condition_on_previous_text=False,
        temperature=[0.0, 0.2, 0.4],
    )
    seg_list = []
    parts = []
    for seg in segments:
        text = seg.text.strip()
        if not text:
            continue
        seg_list.append(
            {
                "start": float(seg.start or 0.0),
                "end": float(seg.end or 0.0),
                "text": text,
            }
        )
        parts.append(text)
    return {
        "text": " ".join(parts).strip(),
        "segments": seg_list,
        "duration": info.duration,
        "language": info.language,
    }


def transcribe_recording(s3_key: str) -> dict:
    path = download_to_temp(s3_key)
    try:
        return transcribe_audio_file(path)
    finally:
        if os.path.exists(path):
            os.remove(path)


def _parse_json_object(raw: str) -> dict:
    cleaned = re.sub(r"```(?:json)?", "", raw).strip()
    return json.loads(cleaned)


def _strip_speaker_labels(text: str) -> str:
    """Remove 'Speaker N:' prefixes so the summarizer sees plain prose."""
    lines = [re.sub(r"^\s*Speaker\s+\d+\s*:\s*", "", ln) for ln in text.splitlines()]
    return " ".join(ln.strip() for ln in lines if ln.strip()).strip()


def _summarize_discussion(transcript: str) -> str:
    """Produce ONE summary paragraph covering the whole discussion.

    Feeds the full transcript (all participants, speaker tags stripped) to the
    best available model: a local LLM via Ollama when present, otherwise T5.
    """
    clean = _strip_speaker_labels(transcript)
    if not clean:
        return ""

    if _ollama_available():
        try:
            summary = _ollama_chat(
                "You are a meeting assistant. Write ONE single, coherent summary "
                "of the entire meeting that captures the key points raised by every "
                "participant. Use plain paragraphs only — no headings, no bullet "
                "points, and no speaker labels.",
                f"Summarize this full meeting discussion:\n\n{clean[:6000]}",
                max_tokens=400,
            )
            if summary.strip():
                return summary.strip()
        except Exception:
            pass

    # Fallback to local T5. Keep short discussions verbatim so no participant's
    # contribution is dropped by the weak model.
    if len(clean.split()) < 60:
        return clean
    return _t5_summarize(clean, 220)


def generate_ai_insights(transcript: str) -> dict:
    summary = _summarize_discussion(transcript)

    default = {
        "title": "Meeting Summary",
        "summary": summary,
        "bullet_summary": [],
        "action_items": [],
        "key_decisions": [],
        "discussion_points": [],
        "open_questions": [],
        "risks": [],
        "next_steps": [],
        "keywords": [],
    }

    if not _ollama_available():
        return default

    prompt = f"""Analyze this meeting transcript and return ONLY valid JSON with keys:
title, bullet_summary (array), action_items (array of {{task, owner, deadline}}),
key_decisions (array), discussion_points (array), open_questions (array),
risks (array), next_steps (array), keywords (array).

Transcript:
{transcript[:6000]}
"""
    try:
        raw = _ollama_chat("You are a meeting intelligence assistant. Return JSON only.", prompt)
        parsed = _parse_json_object(raw)
        default.update({k: parsed.get(k, default[k]) for k in default if k in parsed})
        if parsed.get("title"):
            default["title"] = parsed["title"]
        return default
    except Exception:
        return default


def process_meeting_pipeline(db: Session, meeting_id: str) -> None:
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting or not meeting.recording:
        return

    audio_path = None
    try:
        meeting.status = "transcribing"
        meeting.progress_message = "Transcribing audio..."
        db.commit()

        audio_path = download_to_temp(meeting.recording.s3_key)
        result = transcribe_audio_file(audio_path)
        transcript_text = (result.get("text") or "").strip()
        word_count = len(transcript_text.split())

        if word_count < 2 or transcript_text.lower() in {"you", "thank you", "thanks for watching"}:
            size_bytes = meeting.recording.size_bytes or 0
            meeting.status = "failed"
            meeting.error_message = (
                "No clear speech detected in the recording. "
                f"File size: {size_bytes} bytes. "
                "Allow microphone when starting recording, join the Meet call, "
                "and speak clearly for at least 20 seconds before stopping."
            )
            meeting.progress_message = "No speech detected in recording"
            db.commit()
            return

        # Speaker diarization: label each segment with "Speaker N".
        meeting.progress_message = "Identifying speakers..."
        db.commit()
        segments = result["segments"]
        num_speakers = 1
        try:
            from app.services.diarization import build_diarized_text, diarize_segments

            segments, num_speakers = diarize_segments(audio_path, segments)
            diarized_text = build_diarized_text(segments)
            if diarized_text.strip():
                transcript_text = diarized_text
        except Exception:
            pass

        meeting.duration_seconds = int(result.get("duration") or 0)
        db.merge(
            Transcript(
                meeting_id=meeting.id,
                full_text=transcript_text,
                segments_json=segments,
            )
        )

        # Record detected speakers as participants.
        db.query(Participant).filter(Participant.meeting_id == meeting.id).delete()
        for n in range(1, max(num_speakers, 1) + 1):
            db.add(Participant(meeting_id=meeting.id, name=f"Speaker {n}"))
        db.commit()

        meeting.status = "processing"
        meeting.progress_message = "Generating AI insights..."
        db.commit()

        insights = generate_ai_insights(transcript_text)
        meeting.title = insights.get("title") or meeting.title

        db.merge(
            Summary(
                meeting_id=meeting.id,
                executive_summary=insights["summary"],
                detailed_summary="",
                bullet_summary=insights.get("bullet_summary", []),
                key_decisions=insights.get("key_decisions", []),
                discussion_points=insights.get("discussion_points", []),
                open_questions=insights.get("open_questions", []),
                risks=insights.get("risks", []),
                next_steps=insights.get("next_steps", []),
                keywords=insights.get("keywords", []),
            )
        )

        db.query(ActionItem).filter(ActionItem.meeting_id == meeting.id).delete()
        for item in insights.get("action_items", []):
            if not isinstance(item, dict):
                continue
            db.add(
                ActionItem(
                    meeting_id=meeting.id,
                    task=item.get("task", "Unspecified task"),
                    owner=item.get("owner", "Unassigned"),
                    deadline=item.get("deadline", "Not specified"),
                )
            )

        meeting.status = "ready"
        meeting.progress_message = None
        meeting.ended_at = meeting.ended_at or datetime.utcnow()
        db.commit()
    except Exception as exc:
        meeting.status = "failed"
        meeting.error_message = str(exc)
        meeting.progress_message = "Processing failed"
        db.commit()
    finally:
        if audio_path and os.path.exists(audio_path):
            os.remove(audio_path)
