from fastapi import FastAPI, File, UploadFile, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel
import requests
import shutil
import time
import os
import json
import re
from datetime import datetime

from openai import OpenAI

# To avoid tokenizer warning from HuggingFace
os.environ["TOKENIZERS_PARALLELISM"] = "false"

app = FastAPI()

# ---- API Keys ----
ASSEMBLY_API_KEY = "5d8d89d0b1c74d3c92ab8ce0840e35b8"
OPENROUTER_API_KEY = "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"

headers = {"authorization": ASSEMBLY_API_KEY}
openai_client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OPENROUTER_API_KEY)

# ---- CORS ----
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

HISTORY_FILE = "meeting_history.json"

# ---- Lazy Summarizer ----
def get_summarizer():
    from transformers import pipeline
    return pipeline("summarization", model="t5-small", device=-1)  # Use lighter model for memory

# ---- Utility Functions ----
def load_meeting_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []

def save_meeting_record(summary, action_items):
    history = load_meeting_history()
    history.append({
        "timestamp": datetime.now().isoformat(),
        "summary": summary,
        "action_items": action_items
    })
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)

def get_recent_context(limit=2):
    history = load_meeting_history()
    recent = history[-limit:] if len(history) >= limit else history
    context = ""
    summaries = []
    for item in recent:
        summary = item.get('summary') or ''
        summaries.append(summary)
        context += f"Previous Summary: {summary}\n"
        for act in item.get('action_items', []):
            if isinstance(act, dict):
                context += f"Action: {act.get('task')} | Owner: {act.get('owner')} | Deadline: {act.get('deadline')}\n"
    return context.strip(), summaries

def generate_combined_summary(current_summary_text: str, past_summaries: list):
    combined = " ".join(past_summaries + [current_summary_text])
    combined = combined[:3000]
    if len(combined.split()) < 30:
        return current_summary_text
    summarizer = get_summarizer()
    output = summarizer(combined, max_length=150, min_length=30, do_sample=False)
    return output[0]["summary_text"]

def save_transcript_to_file(transcript: str, filename_prefix: str):
    folder = "transcripts"
    os.makedirs(folder, exist_ok=True)
    file_path = os.path.join(folder, f"{filename_prefix}.txt")
    with open(file_path, "w") as f:
        f.write(transcript)

class TranscriptRequest(BaseModel):
    transcript: str

@app.post("/save-transcript")
def save_transcript_direct(data: TranscriptRequest):
    try:
        path = os.path.join("transcripts")
        os.makedirs(path, exist_ok=True)
        full_path = os.path.join(path, "meeting.txt")

        with open(full_path, "w") as f:
            f.write(data.transcript)

        return {"status": "saved", "path": full_path}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/get-transcript", response_class=PlainTextResponse)
def get_transcript():
    file_path = os.path.join("transcripts", "meeting.txt")
    if not os.path.exists(file_path):
        return PlainTextResponse("Transcript not found", status_code=404)
    with open(file_path, "r") as f:
        return f.read()

def upload_audio_to_assemblyai(file_path):
    with open(file_path, "rb") as f:
        response = requests.post("https://api.assemblyai.com/v2/upload", headers=headers, files={"file": f})
    return response.json()["upload_url"]

def start_transcription(audio_url):
    payload = {
        "audio_url": audio_url,
        "speaker_labels": True,
        "auto_chapters": True
    }
    response = requests.post("https://api.assemblyai.com/v2/transcript", json=payload, headers=headers)
    return response.json()["id"]

def get_transcription_result(transcript_id):
    url = f"https://api.assemblyai.com/v2/transcript/{transcript_id}"
    while True:
        response = requests.get(url, headers=headers)
        data = response.json()
        if data["status"] == "completed":
            return data
        elif data["status"] == "error":
            raise RuntimeError(data["error"])
        time.sleep(3)

def extract_action_items(transcript: str):
    past_context, _ = get_recent_context()
    prompt = f"""
You are an AI assistant. Based on the following meeting transcript and past meeting context, extract clear action items.
Each action item should include:
1. Task
2. Owner
3. Deadline

Format the output as a JSON list with keys: \"task\", \"owner\", and \"deadline\".

{past_context}\n\nCurrent Transcript:\n{transcript}
"""
    try:
        completion = openai_client.chat.completions.create(
            model="mistralai/mistral-7b-instruct",
            messages=[
                {"role": "system", "content": "You are an expert meeting assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=500
        )
        output = completion.choices[0].message.content.strip()
        output = re.sub(r"```(?:json)?", "", output).strip()
        parsed = json.loads(output)
        return parsed if isinstance(parsed, list) else []
    except Exception as e:
        print("OpenRouter extraction error:", e)
        return []

@app.post("/transcribe/from-file")
def transcribe_from_file():
    try:
        file_path = os.path.join("transcripts", "meeting.txt")
        if not os.path.exists(file_path):
            return JSONResponse(status_code=404, content={"error": "File not found."})

        with open(file_path, "r") as f:
            text = f.read()[:3000]

        if len(text.split()) < 30:
            summary_text = text
        else:
            summarizer = get_summarizer()
            summary_output = summarizer(text, max_length=min(len(text.split()), 150), min_length=30, do_sample=False)
            summary_text = summary_output[0]["summary_text"]

        _, past_summaries = get_recent_context()
        combined_summary = generate_combined_summary(summary_text, past_summaries)

        action_items = extract_action_items(text)
        save_meeting_record(summary=combined_summary, action_items=action_items)

        return JSONResponse(content={
            "type": "text",
            "transcript": text,
            "summary": [{
                "summary": combined_summary,
                "headline": "Combined Summary",
                "gist": "Main Idea",
                "start": 0,
                "end": 0
            }],
            "action_items": action_items
        })

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"Internal Server Error: {str(e)}"})

@app.post("/transcribe")
async def transcribe(file: UploadFile = File(...)):
    try:
        filename = file.filename
        extension = filename.split(".")[-1].lower()

        if extension in ["mp3", "wav", "m4a"]:
            temp_filename = f"temp_audio.{extension}"
            with open(temp_filename, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            audio_url = upload_audio_to_assemblyai(temp_filename)
            result = get_transcription_result(start_transcription(audio_url))
            os.remove(temp_filename)

            transcript = ""
            if result.get("utterances"):
                for u in result["utterances"]:
                    transcript += f"{u['speaker']}: {u['text']}\n"
            else:
                transcript = result.get("text", "")

            save_transcript_to_file(transcript, f"meeting_{datetime.now().strftime('%Y%m%d_%H%M%S')}")

            summary = result.get("chapters") or []
            raw_summary = summary[0]['summary'] if summary else ''
            _, past_summaries = get_recent_context()
            combined_summary = generate_combined_summary(raw_summary, past_summaries)

            action_items = extract_action_items(transcript)
            save_meeting_record(summary=combined_summary, action_items=action_items)

            return JSONResponse(content={
                "type": "audio",
                "transcript": transcript,
                "summary": [{
                    "summary": combined_summary,
                    "headline": "Combined Summary",
                    "gist": "Main Idea",
                    "start": 0,
                    "end": 0
                }],
                "action_items": action_items
            })

        elif extension == "txt":
            content = await file.read()
            text = content.decode("utf-8")[:3000]

            if len(text.split()) < 30:
                summary_text = text
            else:
                summarizer = get_summarizer()
                summary_output = summarizer(text, max_length=min(len(text.split()), 150), min_length=30, do_sample=False)
                summary_text = summary_output[0]["summary_text"]

            save_transcript_to_file(text, f"meeting_{datetime.now().strftime('%Y%m%d_%H%M%S')}")

            _, past_summaries = get_recent_context()
            combined_summary = generate_combined_summary(summary_text, past_summaries)

            action_items = extract_action_items(text)
            save_meeting_record(summary=combined_summary, action_items=action_items)

            return JSONResponse(content={
                "type": "text",
                "transcript": text,
                "summary": [{
                    "summary": combined_summary,
                    "headline": "Combined Summary",
                    "gist": "Main Idea",
                    "start": 0,
                    "end": 0
                }],
                "action_items": action_items
            })

        else:
            return JSONResponse(status_code=400, content={"error": "Unsupported file type."})

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"Internal Server Error: {str(e)}"})

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))  # use Render's PORT env if available
    uvicorn.run("main:app", host="0.0.0.0", port=port)
