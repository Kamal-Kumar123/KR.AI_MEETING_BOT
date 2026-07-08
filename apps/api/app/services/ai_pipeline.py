import json
import logging
import os
import re
from datetime import datetime

from sqlalchemy.orm import Session

from app.db.models import ActionItem, Meeting, Participant, Summary, Transcript
from app.services.deepgram_stt import download_to_temp, transcribe_audio_file, transcribe_recording
from app.services.gemini_llm import gemini_available, gemini_chat, gemini_generate_json
from app.services.storage import storage_service

logger = logging.getLogger(__name__)

os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Re-export for backward compatibility with scripts importing from ai_pipeline.
__all__ = [
    "download_to_temp",
    "transcribe_audio_file",
    "transcribe_recording",
    "process_meeting_pipeline",
    "finalize_meeting_insights",
    "generate_ai_insights",
]


SUMMARY_SYSTEM_PROMPT = """You are a senior executive meeting analyst.

Transform raw meeting transcripts into a clear, professional executive summary.

Rules:
- Write ONE cohesive paragraph in third person, past tense (120–250 words for typical meetings)
- Cover: participants or speakers, main topics, key discussion points, decisions, and high-level task assignments
- Use ONLY facts explicitly stated — never invent names, dates, decisions, or tasks
- Do NOT copy the transcript verbatim or include filler ("um", "like", "hello, my name is")
- Do NOT use bullet points, headings, markdown, or speaker labels
- If past meeting context is provided, briefly connect this meeting to ongoing project threads
- Keep action-item details brief here; structured tasks are extracted separately"""


ACTION_ITEMS_SYSTEM_PROMPT = """You are an expert project coordinator extracting actionable tasks from meetings.

Return ONLY a valid JSON array. No markdown, no prose, no wrapper object.

Each element must be an object with exactly these keys:
- "task": specific work to be done (short, actionable phrase)
- "owner": person responsible — use "Unassigned" if no name is given
- "deadline": due date as stated — use "Not specified" if none mentioned

Include every explicit assignment, for example:
- "assign one task to Hassan. He has to complete his work by July 15"
  → {"task": "complete his work", "owner": "Hassan", "deadline": "July 15"}
- "to Aditya, he has to complete his work by July 20"
  → {"task": "complete his work", "owner": "Aditya", "deadline": "July 20"}
- "you need to finish the report by Friday" (no name)
  → {"task": "finish the report", "owner": "Unassigned", "deadline": "Friday"}

Do NOT include: self-introductions, résumé/bio, general discussion, or completed past work.
Return [] only when there are genuinely no task assignments."""


INSIGHTS_SYSTEM_PROMPT = """You are a precise meeting intelligence assistant.

Analyze transcripts and return ONLY valid JSON. Never fabricate facts, tasks, or dates.
Extract action items aggressively — any phrase where someone must do something by a date counts."""


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

    # Deadline boundary: stop at next assignment, sentence, or end.
    _deadline_end = r"(?=\s+and\s+(?:one\s+)?(?:task|project)|\s+and\s+hey\s+|\.\s|\s+so\s+|,\s+so|$)"
    _due = r"(?:by|via|before|until|on|due)"
    _assign_noun = r"(?:task|project|work|assignment)"

    patterns = [
        # "assign one task/project to Hassan. He has to complete ... by/via July 15"
        rf"(?i)assign(?:\s+\w+)?\s+{_assign_noun}\s+to\s+([A-Za-z]+)\.?\s*(?:He|She)\s+has\s+to\s+(.+?)\s+{_due}\s+(.+?)(?=\.|,\s+And|\s+and,|\s+And|\s+to\s+[A-Z]|$)",
        # "to Aditya, he has to complete his work by/via July 20"
        rf"(?i)\bto\s+([A-Za-z]+)\s*,?\s*(?:he|she)\s+has\s+to\s+(.+?)\s+{_due}\s+(.+?)(?=\.|,\s|\s+And|\s+and|\$|$)",
        # "One task is to Aditya. He has to complete his work by 10th of July"
        rf"(?i)(?:one\s+)?(?:task|project)\s+is\s+to\s+([A-Za-z]+)\.?\s*(?:He|She)\s+has\s+to\s+(.+?)\s+{_due}\s+(.+?){_deadline_end}",
        # "hey Hassan, you have to finish your work by 15th of July"
        rf"(?i)\bhey\s+([A-Za-z]+)\s*,?\s*(?:you have to|you need to|please)\s+(.+?)\s+{_due}\s+(.+?){_deadline_end}",
        # "assign task to Aritya, you have to finish your work by 10th of July"
        rf"(?i)\bto\s+([A-Za-z]+)\s*,?\s*(?:you have to|you need to|please)\s+(.+?)\s+{_due}\s+(.+?){_deadline_end}",
        # "Aditya will submit the report by July 10"
        rf"(?i)\b([A-Za-z]+)\s+will\s+(.+?)\s+{_due}\s+(.+?)(?=\.|,|\s+and\s+|$)",
        # "John, please send the proposal by Friday"
        rf"(?i)\b([A-Za-z]+)\s*,?\s*please\s+(.+?)\s+{_due}\s+(.+?)(?=\.|,|\s+and\s+|$)",
        # "Aditya has to complete his work by 10th of July"
        rf"(?i)\b([A-Za-z]+)\s+has\s+to\s+(.+?)\s+{_due}\s+(.+?)(?=\.|,|\s+and\s+|$)",
        # "assigned to Aditya ... deadline 10th July"
        rf"(?i)\bassigned\s+to\s+([A-Za-z]+)[^.]*?(?:{_due}|deadline)\s+(.+?)(?=\.|,|\s+and\s+|$)",
        # "you have to complete your work by 10th of July" (no name — use Unassigned)
        rf"(?i)(?:you have to|you need to|must)\s+(.+?)\s+{_due}\s+(.+?)(?=\.|,|\s+and\s+|This is|$)",
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
    """Dedicated Gemini pass: assign tasks to people with deadlines when explicitly stated."""
    clean = _strip_speaker_labels(transcript)
    if not clean:
        return []

    if not gemini_available():
        return []

    context_block = ""
    if past_context:
        context_block = f"Context from earlier meetings (reference only):\n{past_context[:1500]}\n\n"

    prompt = f"""{context_block}Extract all action items from this meeting transcript.

Transcript:
{clean[:6000]}"""
    try:
        raw = gemini_generate_json(ACTION_ITEMS_SYSTEM_PROMPT, prompt, max_tokens=1200)
        parsed = _parse_json_array(raw)
        return _normalize_action_items(parsed)
    except Exception as exc:
        logger.warning("Gemini action-item extraction failed, using heuristics only: %s", exc)
        return []


def _generate_summary_paragraph(transcript: str, past_context: str = "") -> str:
    """Dedicated Gemini pass for executive summary."""
    clean = _strip_speaker_labels(transcript)
    if not clean or not gemini_available():
        return ""

    context_block = ""
    if past_context:
        context_block = (
            f"Past meetings in this project series (continuity only — do NOT invent facts):\n"
            f"{past_context[:2500]}\n\n"
        )

    prompt = f"""{context_block}Write an executive summary of this meeting:

{clean[:8000]}"""
    try:
        summary = gemini_chat(SUMMARY_SYSTEM_PROMPT, prompt, max_tokens=600)
        return summary.strip()
    except Exception as exc:
        logger.warning("Gemini summary generation failed: %s", exc)
        return ""


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

    if gemini_available():
        try:
            summary = gemini_chat(
                SUMMARY_SYSTEM_PROMPT,
                f"{context_block}Summarize this full meeting discussion:\n\n{clean[:6000]}",
                max_tokens=600,
            )
            if summary.strip():
                return summary.strip()
        except Exception as exc:
            logger.warning("Gemini discussion summary failed: %s", exc)

    if len(clean.split()) < 60:
        return clean
    return clean[:500]


def _token_budget(transcript: str) -> int:
    """Shorter transcripts need fewer generated tokens."""
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

    if not gemini_available():
        return default

    context_block = ""
    if past_context:
        context_block = (
            f"Past meetings in this project series (continuity only — do NOT invent facts):\n"
            f"{past_context[:2500]}\n\n"
        )

    max_tokens = _token_budget(clean)
    prompt = f"""{context_block}Analyze this meeting transcript.

Return JSON with these keys:
- "title": short descriptive title (max 8 words) from what was discussed
- "summary": leave as empty string "" — summary is generated separately
- "bullet_summary": array of 3–8 main points actually stated
- "action_items": array of {{"task", "owner", "deadline"}} for EVERY task assignment
- "key_decisions": array (empty [] if none)
- "discussion_points": array of topics discussed
- "open_questions": array (empty [] if none)
- "risks": array (empty [] if none)
- "next_steps": array (empty [] if none)
- "keywords": array of 5–12 key terms

Transcript:
{clean[:6000]}"""
    try:
        raw = gemini_generate_json(INSIGHTS_SYSTEM_PROMPT, prompt, max_tokens=max_tokens)
        parsed = _parse_json_object(raw)
        default.update({k: parsed.get(k, default[k]) for k in default if k in parsed})
        if parsed.get("title"):
            default["title"] = parsed["title"]

        summary = _generate_summary_paragraph(clean, past_context)
        if summary:
            default["summary"] = summary
        elif parsed.get("summary"):
            default["summary"] = str(parsed["summary"]).strip()

        default["action_items"] = _normalize_action_items(parsed.get("action_items", []))
        return default
    except Exception as exc:
        logger.warning("Gemini insights generation failed, using fallbacks: %s", exc)
        summary = _generate_summary_paragraph(clean, past_context)
        if summary:
            default["summary"] = summary
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

        # Speaker labels: Deepgram diarization when available, else local fallback.
        meeting.progress_message = "Identifying speakers..."
        db.commit()
        segments = result["segments"]
        num_speakers = int(result.get("num_speakers") or 1)
        has_dg_speakers = any(s.get("speaker") for s in segments)
        try:
            from app.services.diarization import build_diarized_text, diarize_segments

            if has_dg_speakers:
                diarized_text = build_diarized_text(segments)
                if diarized_text.strip():
                    transcript_text = diarized_text
                num_speakers = len({s.get("speaker") for s in segments if s.get("speaker")}) or 1
            elif audio_path:
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
