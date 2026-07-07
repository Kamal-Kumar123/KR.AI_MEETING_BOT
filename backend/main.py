from fastapi import FastAPI, File, UploadFile, Form, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field
import shutil
import os
import json
import re
from datetime import datetime

from config import ENV, FRONTEND_URL, OLLAMA_MODEL, PORT, get_allowed_origins
from llm import chat, is_ollama_available, list_models
from meeting_context import normalize_meeting_context
from meeting_store import build_share_url, get_meeting_by_id, save_meeting_record
from rag import get_rag_service
from transcription import SUPPORTED_AUDIO_EXTENSIONS, is_diarization_available, is_whisper_ready, transcribe_audio_file

os.environ["TOKENIZERS_PARALLELISM"] = "false"

app = FastAPI(title="KR.AI Meeting Bot", description="Meeting intelligence — local or Render + Vercel")

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_checks():
    from meeting_store import HISTORY_FILE

    rag = get_rag_service()
    indexed = rag.migrate_from_json_history(HISTORY_FILE)
    if indexed:
        print(f"RAG: indexed {indexed} chunks from {HISTORY_FILE}")

    if is_ollama_available():
        print(f"Ollama ready with model: {OLLAMA_MODEL}")
    else:
        print(f"WARNING: Ollama not ready. Run: ollama pull {OLLAMA_MODEL}")


def get_summarizer():
    from transformers import pipeline

    return pipeline("text2text-generation", model="t5-small", device=-1)


def summarize_text(text: str) -> str:
    if len(text.split()) < 30:
        return text
    summarizer = get_summarizer()
    summary_output = summarizer(
        "summarize: " + text,
        max_length=min(len(text.split()), 150),
        min_length=30,
        do_sample=False,
    )
    return summary_output[0]["generated_text"]


def generate_combined_summary(current_summary_text: str, past_summaries: list, use_rag: bool):
    if not use_rag or not past_summaries:
        return current_summary_text

    combined = " ".join(past_summaries + [current_summary_text])
    combined = combined[:3000]
    if len(combined.split()) < 30:
        return current_summary_text

    summarizer = get_summarizer()
    output = summarizer("summarize: " + combined, max_length=150, min_length=30, do_sample=False)
    return output[0]["generated_text"]


def parse_json_list(raw_text: str) -> list:
    cleaned = re.sub(r"```(?:json)?", "", raw_text).strip()
    parsed = json.loads(cleaned)
    return parsed if isinstance(parsed, list) else []


def extract_action_items(transcript: str, past_context: str):
    if not is_ollama_available():
        print("Ollama unavailable — action items skipped. Run: ollama pull mistral")
        return []

    context_block = f"{past_context}\n\n" if past_context else ""
    prompt = f"""Based on this meeting transcript, extract action items.
Return ONLY a JSON array. Each item must have keys: "task", "owner", "deadline".
Use "Unassigned" for owner and "Not specified" for deadline if unclear.

{context_block}Current Transcript:
{transcript[:3000]}
"""
    try:
        output = chat(
            system="You are an expert meeting assistant. Return valid JSON only.",
            user=prompt,
            temperature=0.2,
            max_tokens=600,
        )
        return parse_json_list(output)
    except Exception as exc:
        print(f"Ollama action-item extraction error: {exc}")
        return []


def build_meeting_response(
    meeting_id,
    mode,
    series_id,
    use_rag,
    past_context,
    content_type,
    transcript,
    combined_summary,
    action_items,
):
    return {
        "meeting_id": meeting_id,
        "mode": mode,
        "series_id": series_id,
        "use_rag": use_rag,
        "rag_context_used": bool(past_context),
        "stack": "free-local",
        "type": content_type,
        "transcript": transcript,
        "summary": [
            {
                "summary": combined_summary,
                "headline": "Meeting Summary",
                "gist": "Main Idea",
                "start": 0,
                "end": 0,
            }
        ],
        "action_items": action_items,
        "share_url": build_share_url(meeting_id),
    }


def process_meeting_text(
    text: str,
    mode: str = "standalone",
    series_id: str | None = None,
    content_type: str = "text",
    source: str = "upload",
):
    try:
        mode, series_id, use_rag = normalize_meeting_context(mode, series_id)
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"error": str(exc)})

    processing_text = text[:3000]
    summary_text = summarize_text(processing_text)

    rag = get_rag_service()
    past_context, past_summaries = rag.get_context_for_transcript(
        processing_text,
        series_id=series_id,
        use_rag=use_rag,
    )
    combined_summary = generate_combined_summary(summary_text, past_summaries, use_rag)
    action_items = extract_action_items(processing_text, past_context)
    meeting_id = save_meeting_record(
        transcript=text,
        summary=combined_summary,
        action_items=action_items,
        mode=mode,
        series_id=series_id,
        use_rag=use_rag,
        source=source,
    )

    return build_meeting_response(
        meeting_id,
        mode,
        series_id,
        use_rag,
        past_context,
        content_type,
        text,
        combined_summary,
        action_items,
    )


def save_transcript_to_file(transcript: str, filename_prefix: str):
    folder = "transcripts"
    os.makedirs(folder, exist_ok=True)
    file_path = os.path.join(folder, f"{filename_prefix}.txt")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(transcript)


class TranscriptRequest(BaseModel):
    transcript: str


class ExtensionFinishRequest(BaseModel):
    transcript: str
    mode: str = "standalone"
    series_id: str | None = None


class RAGQueryRequest(BaseModel):
    question: str
    series_id: str
    top_k: int = 5
    use_llm: bool = True


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "env": ENV,
        "stack": "free-local",
        "frontend_url": FRONTEND_URL,
        "ollama": is_ollama_available(),
        "ollama_model": OLLAMA_MODEL,
        "ollama_models_installed": list_models(),
        "whisper": is_whisper_ready(),
        "diarization": is_diarization_available(),
        "rag_chunks": get_rag_service().get_stats()["total_chunks"],
    }


@app.post("/extension/finish-meeting")
def extension_finish_meeting(data: ExtensionFinishRequest):
    """Extension calls this when meeting ends — process + return shareable link."""
    try:
        if not data.transcript.strip():
            return JSONResponse(status_code=400, content={"error": "Transcript is empty."})

        os.makedirs("transcripts", exist_ok=True)
        with open(os.path.join("transcripts", "meeting.txt"), "w", encoding="utf-8") as f:
            f.write(data.transcript)

        result = process_meeting_text(
            data.transcript,
            mode=data.mode,
            series_id=data.series_id,
            content_type="extension",
            source="extension",
        )
        if isinstance(result, JSONResponse):
            return result
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/meetings/{meeting_id}")
def get_shared_meeting(meeting_id: str):
    """Public share link — anyone with the link can view meeting results."""
    meeting = get_meeting_by_id(meeting_id)
    if not meeting:
        return JSONResponse(status_code=404, content={"error": "Meeting not found."})

    mid = meeting.get("meeting_id") or meeting.get("timestamp")
    return {
        "meeting_id": mid,
        "timestamp": meeting.get("timestamp"),
        "mode": meeting.get("mode", "standalone"),
        "series_id": meeting.get("series_id"),
        "source": meeting.get("source", "upload"),
        "transcript": meeting.get("transcript", ""),
        "summary": meeting.get("summary", ""),
        "action_items": meeting.get("action_items", []),
        "share_url": meeting.get("share_url") or build_share_url(mid),
    }


@app.post("/save-transcript")
def save_transcript_direct(data: TranscriptRequest):
    try:
        os.makedirs("transcripts", exist_ok=True)
        full_path = os.path.join("transcripts", "meeting.txt")
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(data.transcript)
        return {"status": "saved", "path": full_path}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/get-transcript", response_class=PlainTextResponse)
def get_transcript():
    file_path = os.path.join("transcripts", "meeting.txt")
    if not os.path.exists(file_path):
        return PlainTextResponse("Transcript not found", status_code=404)
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


@app.post("/transcribe/from-file")
def transcribe_from_file(
    mode: str = Query(default="standalone"),
    series_id: str | None = Query(default=None),
):
    try:
        file_path = os.path.join("transcripts", "meeting.txt")
        if not os.path.exists(file_path):
            return JSONResponse(status_code=404, content={"error": "File not found."})

        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()

        result = process_meeting_text(text, mode=mode, series_id=series_id, content_type="text")
        if isinstance(result, JSONResponse):
            return result
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"Internal Server Error: {str(e)}"})


@app.post("/transcribe")
async def transcribe(
    file: UploadFile = File(...),
    mode: str = Form(default="standalone"),
    series_id: str | None = Form(default=None),
):
    try:
        filename = file.filename or "upload"
        extension = filename.split(".")[-1].lower()

        if extension in SUPPORTED_AUDIO_EXTENSIONS:
            temp_filename = f"temp_audio.{extension}"
            with open(temp_filename, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            try:
                whisper_result = transcribe_audio_file(temp_filename)
                transcript = whisper_result["text"]
            finally:
                if os.path.exists(temp_filename):
                    os.remove(temp_filename)

            if not transcript.strip():
                return JSONResponse(status_code=400, content={"error": "No speech detected in audio file."})

            save_transcript_to_file(transcript, f"meeting_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            result = process_meeting_text(transcript, mode=mode, series_id=series_id, content_type="audio")
            if isinstance(result, JSONResponse):
                return result

            result["transcription"] = {
                "engine": whisper_result["engine"],
                "model": whisper_result["model"],
                "cost": whisper_result["cost"],
                "language": whisper_result["language"],
                "duration_seconds": whisper_result["duration_seconds"],
                "segment_count": len(whisper_result["segments"]),
                "diarization": whisper_result.get("diarization", {"enabled": False}),
            }
            result["transcript_segments"] = whisper_result["segments"]
            return JSONResponse(content=result)

        if extension == "txt":
            content = await file.read()
            text = content.decode("utf-8")
            result = process_meeting_text(text, mode=mode, series_id=series_id, content_type="text")
            if isinstance(result, JSONResponse):
                return result
            save_transcript_to_file(text, f"meeting_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            return JSONResponse(content=result)

        return JSONResponse(
            status_code=400,
            content={
                "error": f"Unsupported file type. Use {', '.join(sorted(SUPPORTED_AUDIO_EXTENSIONS))}, or txt."
            },
        )

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"Internal Server Error: {str(e)}"})


@app.get("/meeting/series")
def list_meeting_series():
    rag = get_rag_service()
    return {"series_ids": rag.get_stats()["series_ids"]}


@app.get("/rag/stats")
def rag_stats(series_id: str | None = Query(default=None)):
    rag = get_rag_service()
    return rag.get_stats(series_id=series_id)


@app.post("/rag/query")
def rag_query(data: RAGQueryRequest):
    try:
        if not data.series_id.strip():
            return JSONResponse(status_code=400, content={"error": "series_id is required for RAG queries"})

        rag = get_rag_service()
        retrieval = rag.answer_question(data.question, top_k=data.top_k, series_id=data.series_id.strip())

        if not data.use_llm or not retrieval["sources"]:
            return retrieval

        if not is_ollama_available():
            return JSONResponse(
                status_code=503,
                content={"error": f"Ollama not available. Run: ollama pull {OLLAMA_MODEL}"},
            )

        prompt = f"""Answer using only this meeting context from series '{data.series_id}'.
If the answer is not in the context, say you could not find it.

Context:
{retrieval['context']}

Question: {data.question}
"""
        answer = chat(
            system="You are a meeting memory assistant.",
            user=prompt,
            temperature=0.2,
            max_tokens=400,
        )
        return {
            "question": data.question,
            "series_id": data.series_id,
            "answer": answer,
            "sources": retrieval["sources"],
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=PORT)
