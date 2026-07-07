import os

# Environment: local | production
ENV = os.environ.get("ENV", "local")
IS_RENDER = os.environ.get("RENDER") == "true"
IS_VERCEL = os.environ.get("VERCEL") == "1"

# Server
PORT = int(os.environ.get("PORT", 10000))

# Local Whisper (free STT)
WHISPER_MODEL = os.environ.get("WHISPER_MODEL", "base")
WHISPER_DEVICE = os.environ.get("WHISPER_DEVICE", "cpu")

# Speaker diarization (free with HuggingFace token)
HF_TOKEN = os.environ.get("HF_TOKEN", os.environ.get("HUGGINGFACE_TOKEN", ""))
ENABLE_DIARIZATION = os.environ.get("ENABLE_DIARIZATION", "true").lower() == "true"

# Local Ollama (free LLM) — on Render, point to your machine via tunnel or leave unset
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "mistral")

# URLs
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")
BACKEND_URL = os.environ.get("BACKEND_URL", f"http://localhost:{PORT}")

HISTORY_FILE = "meeting_history.json"
CHROMA_DIR = os.environ.get("CHROMA_DIR", "chroma_data")


def get_allowed_origins() -> list[str]:
    """CORS origins — set ALLOWED_ORIGINS for Render + Vercel."""
    raw = os.environ.get("ALLOWED_ORIGINS", "").strip()
    if raw:
        return [origin.strip() for origin in raw.split(",") if origin.strip()]

    origins = ["http://localhost:3000", "http://127.0.0.1:3000"]
    if FRONTEND_URL and FRONTEND_URL not in origins:
        origins.append(FRONTEND_URL)
    return origins
