
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

from transformers import pipeline
from openai import OpenAI

# To avoid tokenizer warning from HuggingFace
os.environ["TOKENIZERS_PARALLELISM"] = "false"

app = FastAPI()

# ---- Summarizer ----
summarizer = pipeline("summarization", model="sshleifer/distilbart-cnn-12-6", device=-1)

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
