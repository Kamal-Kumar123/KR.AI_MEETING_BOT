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


_ollama_ok: bool | None = None


def _ollama_available() -> bool:
    global _ollama_ok
    if _ollama_ok is not None:
        return _ollama_ok
    try:
        r = requests.get(f"{settings.ollama_base_url}/api/tags", timeout=5)
        if r.status_code != 200:
            _ollama_ok = False
            return False
        names = [m.get("name", "") for m in r.json().get("models", [])]
        _ollama_ok = any(settings.ollama_model in n for n in names)
    except Exception:
        _ollama_ok = False
    return _ollama_ok


def _ollama_chat(system: str, user: str, max_tokens: int = 800) -> str:
    response = requests.post(
        f"{settings.ollama_base_url}/api/chat",
        json={
            "model": settings.ollama_model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "stream": False,
            "options": {
                "temperature": 0.2,
                "num_predict": max_tokens,
                "num_ctx": 4096,
            },
        },
        timeout=120,
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
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise


def _parse_json_array(raw: str) -> list:
    cleaned = re.sub(r"```(?:json)?", "", raw).strip()
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\[.*\]", cleaned, re.DOTALL)
        if not match:
            raise
        parsed = json.loads(match.group())
    if isinstance(parsed, dict) and "action_items" in parsed:
        parsed = parsed["action_items"]
    if not isinstance(parsed, list):
        return []
    return parsed


def _normalize_action_items(raw) -> list[dict]:
    """Coerce LLM output into {task, owner, deadline} objects."""
    if not raw:
        return []
    if isinstance(raw, dict):
        raw = [raw]
    if not isinstance(raw, list):
        return []

    items: list[dict] = []
    for item in raw:
        if isinstance(item, str):
            text = item.strip()
            if text:
                items.append({"task": text, "owner": "Unassigned", "deadline": "Not specified"})
            continue
        if not isinstance(item, dict):
            continue
        task = (
            item.get("task")
            or item.get("Task")
            or item.get("action")
            or item.get("description")
            or item.get("text")
            or item.get("work")
            or item.get("item")
        )
        owner = (
            item.get("owner")
            or item.get("assignee")
            or item.get("assigned_to")
            or item.get("person")
            or item.get("name")
            or item.get("responsible")
            or "Unassigned"
        )
        deadline = (
            item.get("deadline")
            or item.get("due_date")
            or item.get("due")
            or item.get("date")
            or item.get("by")
            or "Not specified"
        )
        if task and str(task).strip():
            items.append(
                {
                    "task": str(task).strip(),
                    "owner": str(owner).strip() or "Unassigned",
                    "deadline": str(deadline).strip() or "Not specified",
                }
            )
    return items


def _merge_action_items(*sources: list[dict]) -> list[dict]:
    """Merge action item lists, dedupe by owner + task + deadline."""
    merged: list[dict] = []
    seen: set[tuple[str, str, str]] = set()
    for source in sources:
        for item in _normalize_action_items(source):
            key = (
                item["owner"].lower(),
                item["task"].lower()[:80],
                item["deadline"].lower()[:40],
            )
            if key in seen:
                continue
            seen.add(key)
            merged.append(item)
    return merged


def _extract_action_items_heuristic(text: str) -> list[dict]:
    """Rule-based extraction — always runs as fallback; catches common speech patterns."""
    clean = _strip_speaker_labels(text)
    if not clean:
        return []

    items: list[dict] = []
    seen: set[tuple[str, str, str]] = set()

    def add(owner: str, task: str, deadline: str) -> None:
        owner = owner.strip().strip(".") or "Unassigned"
        task = task.strip().strip(",").strip()
        deadline = (deadline or "Not specified").strip().strip(",").strip().rstrip(".")
        if not task:
            return
        skip = {
            "i", "we", "the", "this", "that", "my", "your", "a", "an",
            "he", "she", "they", "one", "two", "today", "hello", "like", "here",
        }
        if owner.lower() in skip:
            return
        if owner != "Unassigned" and not owner[0].isupper():
            return
        key = (owner.lower(), task.lower()[:80], deadline.lower()[:40])
        if key in seen:
            return
        seen.add(key)
        items.append({"task": task, "owner": owner, "deadline": deadline or "Not specified"})

    # Deadline boundary: stop at "and one task", next sentence, or end.
    _deadline_end = r"(?=\s+and\s+(?:one\s+)?task|\s+and\s+hey\s+|\.\s|\s+so\s+|,\s+so|$)"

    patterns = [
        # "One task is to Aditya. He has to complete his work by 10th of July"
        rf"(?i)(?:one\s+)?task\s+is\s+to\s+([A-Za-z]+)\.?\s*(?:He|She)\s+has\s+to\s+(.+?)\s+by\s+(.+?){_deadline_end}",
        # "hey Hassan, you have to finish your work by 15th of July"
        rf"(?i)\bhey\s+([A-Za-z]+)\s*,?\s*(?:you have to|you need to|please)\s+(.+?)\s+by\s+(.+?){_deadline_end}",
        # "assign task to Aritya, you have to finish your work by 10th of July"
        rf"(?i)\bto\s+([A-Za-z]+)\s*,?\s*(?:you have to|you need to|please)\s+(.+?)\s+by\s+(.+?){_deadline_end}",
        # "Aditya will submit the report by July 10"
        r"(?i)\b([A-Za-z]+)\s+will\s+(.+?)\s+by\s+(.+?)(?=\.|,|\s+and\s+|$)",
        # "John, please send the proposal by Friday"
        r"(?i)\b([A-Za-z]+)\s*,?\s*please\s+(.+?)\s+by\s+(.+?)(?=\.|,|\s+and\s+|$)",
        # "Aditya has to complete his work by 10th of July"
        r"(?i)\b([A-Za-z]+)\s+has\s+to\s+(.+?)\s+by\s+(.+?)(?=\.|,|\s+and\s+|$)",
        # "assigned to Aditya ... deadline 10th July"
        r"(?i)\bassigned\s+to\s+([A-Za-z]+)[^.]*?(?:by|before|deadline)\s+(.+?)(?=\.|,|\s+and\s+|$)",
        # "you have to complete your work by 10th of July" (no name — use Unassigned)
        r"(?i)(?:you have to|you need to|must)\s+(.+?)\s+by\s+(.+?)(?=\.|,|\s+and\s+|This is|$)",
        # "deadline ... 10th of July" with preceding task phrase
        r"(?i)\bcomplete\s+(?:your|the)\s+work\s+by\s+(.+?)(?=\.|,|\s+and\s+|$)",
    ]

    for pat in patterns:
        for m in re.finditer(pat, clean):
            groups = m.groups()
            if len(groups) == 3:
                add(groups[0], groups[1], groups[2])
            elif len(groups) == 2:
                # Could be (owner, deadline) or (task, deadline) for unnamed
                g0, g1 = groups[0], groups[1]
                if re.match(r"(?i)(?:you have to|you need to|complete|finish|submit)", g0):
                    add("Unassigned", g0, g1)
                else:
                    add(g0, "Complete assigned work", g1)
            elif len(groups) == 1:
                add("Unassigned", "complete your work", groups[0])

    return items


def collect_action_items(transcript: str, past_context: str, insights: dict) -> list[dict]:
    """LLM + insights + heuristic — merge all sources so nothing is missed."""
    llm_items = extract_action_items(transcript, past_context=past_context)
    insight_items = _normalize_action_items(insights.get("action_items", []))
    heuristic_items = _extract_action_items_heuristic(transcript)
    return _merge_action_items(llm_items, insight_items, heuristic_items)


def extract_action_items(transcript: str, past_context: str = "") -> list[dict]:
    """Dedicated pass: assign tasks to people with deadlines when explicitly stated."""
    clean = _strip_speaker_labels(transcript)
    if not clean or not _ollama_available():
        return []

    context_block = ""
    if past_context:
        context_block = f"Context from earlier meetings (reference only):\n{past_context[:1500]}\n\n"

    prompt = f"""{context_block}Extract action items from this meeting transcript.

An action item is when someone assigns a specific task to a person (or to "you"/team), with or without a deadline.
If no person name is given, use owner "Unassigned".

INCLUDE examples like:
- "One task is to Aditya. He has to complete his work by 10th of July"
- "you have to complete your work by 10th of July" → owner: Unassigned
- "Like here you have to complete your work by 10th of July" → task + deadline, owner Unassigned if no name

Do NOT include past completed work, self-introductions, or general discussion without a clear assigned task.

Return ONLY a JSON array. Each object must have exactly these keys:
- "task": what needs to be done (short, specific)
- "owner": person responsible (use "Unassigned" if unclear)
- "deadline": when it is due (use "Not specified" if not stated)

Example output:
[
  {{"task": "complete his work", "owner": "Aditya", "deadline": "10th of July"}},
  {{"task": "complete his work", "owner": "Hasan", "deadline": "15th of July, 2026"}}
]

Transcript:
{clean[:4000]}"""
    try:
        raw = _ollama_chat(
            "You extract meeting action items. Return a valid JSON array only, no markdown.",
            prompt,
            max_tokens=800,
        )
        parsed = _parse_json_array(raw)
        return _normalize_action_items(parsed)
    except Exception:
        return []


def _strip_speaker_labels(text: str) -> str:
    """Remove 'Speaker N:' prefixes so the summarizer sees plain prose."""
    lines = [re.sub(r"^\s*Speaker\s+\d+\s*:\s*", "", ln) for ln in text.splitlines()]
    return " ".join(ln.strip() for ln in lines if ln.strip()).strip()


def _summarize_discussion(
    transcript: str,
    past_context: str = "",
    past_summaries: list[str] | None = None,
) -> str:
    """Produce ONE summary paragraph covering the whole discussion."""
    clean = _strip_speaker_labels(transcript)
    if not clean:
        return ""

    context_block = ""
    if past_context:
        context_block = (
            f"Context from earlier meetings in this project series:\n{past_context[:2500]}\n\n"
        )

    if _ollama_available():
        try:
            summary = _ollama_chat(
                "You are a meeting assistant. Write ONE single, coherent summary "
                "of the entire meeting that captures the key points raised by every "
                "participant. If past meeting context is provided, connect this meeting "
                "to ongoing threads in the series. Use plain paragraphs only — no headings, "
                "no bullet points, and no speaker labels.",
                f"{context_block}Summarize this full meeting discussion:\n\n{clean[:6000]}",
                max_tokens=400,
            )
            if summary.strip():
                return summary.strip()
        except Exception:
            pass

    if past_summaries and len(clean.split()) >= 30:
        combined = " ".join(past_summaries + [clean])[:3000]
        if len(combined.split()) >= 30:
            return _t5_summarize(combined, 220)

    if len(clean.split()) < 60:
        return clean
    return _t5_summarize(clean, 220)


def _token_budget(transcript: str) -> int:
    """Shorter transcripts need fewer generated tokens — keeps Ollama fast."""
    words = len(transcript.split())
    if words < 120:
        return 500
    if words < 400:
        return 700
    return 900


def generate_ai_insights(transcript: str, past_context: str = "") -> dict:
    clean = _strip_speaker_labels(transcript)
    default = {
        "title": "Meeting Summary",
        "summary": clean or transcript[:500],
        "bullet_summary": [],
        "action_items": [],
        "key_decisions": [],
        "discussion_points": [],
        "open_questions": [],
        "risks": [],
        "next_steps": [],
        "keywords": [],
    }

    if not clean:
        return default

    if not _ollama_available():
        if len(clean.split()) >= 60:
            default["summary"] = _t5_summarize(clean, 220)
        return default

    context_block = ""
    if past_context:
        context_block = (
            f"Past meetings in this project series (continuity only — do NOT invent facts):\n"
            f"{past_context[:2500]}\n\n"
        )

    max_tokens = _token_budget(clean)
    prompt = f"""{context_block}Analyze this meeting transcript. Extract ONLY information explicitly stated.
Do NOT invent, assume, guess, or infer anything not actually said.

Return ONLY valid JSON with these keys:
- "title": short descriptive title from what was discussed
- "summary": ONE coherent paragraph summarizing the entire meeting (plain prose, no bullets).
  Cover who spoke and what was discussed. Do NOT list structured action items here — those go in action_items.
- "bullet_summary": array of main points actually said
- "action_items": array of {{"task", "owner", "deadline"}} for every explicit task assignment in the meeting.
  Example: speaker assigns "finish your work by 10th of July" to Aritya →
  {{"task": "finish your work", "owner": "Aritya", "deadline": "10th of July"}}.
  Include ALL assignments with person + task + deadline when stated. Empty [] only if none.
- "key_decisions": array (empty [] if none)
- "discussion_points": array of topics discussed
- "open_questions": array (empty [] if none)
- "risks": array (empty [] if none)
- "next_steps": array (empty [] if none)
- "keywords": array of key terms from the transcript

Transcript:
{clean[:6000]}"""
    try:
        raw = _ollama_chat(
            "You are a precise meeting assistant. Return JSON only. Never fabricate tasks or facts.",
            prompt,
            max_tokens=max_tokens,
        )
        parsed = _parse_json_object(raw)
        default.update({k: parsed.get(k, default[k]) for k in default if k in parsed})
        if parsed.get("title"):
            default["title"] = parsed["title"]
        if parsed.get("summary"):
            default["summary"] = str(parsed["summary"]).strip()
        default["action_items"] = _normalize_action_items(parsed.get("action_items", []))
        return default
    except Exception:
        if len(clean.split()) >= 60:
            default["summary"] = _t5_summarize(clean, 220)
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

        ext = (meeting.recording.s3_key or "").rsplit(".", 1)[-1].lower()
        audio_path = None
        if ext == "txt":
            raw = storage_service.download_bytes(meeting.recording.s3_key)
            transcript_text = raw.decode("utf-8", errors="replace").strip()
            result = {"text": transcript_text, "segments": [], "duration": 0, "language": "en"}
        else:
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
        # Replace any existing transcript so re-processing a meeting works
        # (meeting_id is unique — we can't just insert a second row).
        db.query(Transcript).filter(Transcript.meeting_id == meeting.id).delete()
        db.flush()
        db.add(
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

        # Always pause here so the website can ask standalone vs connected.
        # Summary/action-items run only after POST /meeting/{id}/configure.
        db.query(Summary).filter(Summary.meeting_id == meeting.id).delete()
        db.query(ActionItem).filter(ActionItem.meeting_id == meeting.id).delete()
        meeting.meeting_mode = None
        meeting.series_id = None
        meeting.use_rag = False
        meeting.rag_context_used = False
        meeting.status = "awaiting_config"
        meeting.progress_message = "Choose standalone or connected meeting type"
        db.commit()
    except Exception as exc:
        meeting.status = "failed"
        meeting.error_message = str(exc)
        meeting.progress_message = "Processing failed"
        db.commit()
    finally:
        if audio_path and os.path.exists(audio_path):
            os.remove(audio_path)


def finalize_meeting_insights(db: Session, meeting_id: str) -> None:
    """Generate summary/action items after user picks standalone vs connected."""
    from app.services.meeting_context import normalize_meeting_context
    from app.services.rag import get_rag_service

    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting or not meeting.transcript:
        return

    try:
        if not meeting.meeting_mode:
            meeting.status = "awaiting_config"
            meeting.progress_message = "Choose standalone or connected meeting type"
            db.commit()
            return

        mode, series_id, use_rag = normalize_meeting_context(meeting.meeting_mode, meeting.series_id)
        meeting.meeting_mode = mode
        meeting.series_id = series_id
        meeting.use_rag = use_rag
        meeting.status = "processing"
        meeting.progress_message = "Generating AI insights..."
        db.commit()

        transcript_text = meeting.transcript.full_text or ""
        rag = get_rag_service()
        past_context, _past_summaries = rag.get_context_for_transcript(
            transcript_text,
            series_id=series_id,
            use_rag=use_rag,
            exclude_meeting_id=meeting.id,
        )
        meeting.rag_context_used = bool(past_context)

        insights = generate_ai_insights(transcript_text, past_context=past_context)
        action_items = collect_action_items(transcript_text, past_context, insights)
        insights["action_items"] = action_items

        default_titles = ("Untitled Meeting", "Meeting Recording", "Meeting Summary", "")
        if insights.get("title") and (not meeting.title or meeting.title in default_titles):
            meeting.title = insights.get("title")

        db.query(Summary).filter(Summary.meeting_id == meeting.id).delete()
        db.flush()
        db.add(
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
        for item in action_items:
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

        if use_rag and series_id:
            rag.index_meeting(
                meeting_id=meeting.id,
                transcript=transcript_text,
                summary=insights["summary"],
                action_items=action_items,
                timestamp=meeting.created_at.isoformat() if meeting.created_at else None,
                mode=mode,
                series_id=series_id,
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
