# KR.AI Meeting Bot — 100% Free Local Stack

GenAI meeting assistant for college projects. **No paid APIs** — everything runs on your laptop.

## Free stack

| Step | Tool |
|------|------|
| Capture | Chrome extension (Web Speech API on Zoom) |
| Upload notes | `.txt` file |
| Upload recording | Local Zoom recording → `.mp3` / `.wav` |
| Transcribe audio | **Whisper** (`faster-whisper`) |
| Summarize | **T5-small** (local) |
| Action items | **Ollama** (local Mistral/Llama) |
| Meeting memory | **ChromaDB** + sentence-transformers (RAG) |
| Run | `localhost` |

---

## Prerequisites

1. **Python 3.10+**
2. **Node.js** (for frontend)
3. **Ollama** — https://ollama.com
4. **Chrome** (for extension)

---

## Setup (one time)

### 1. Install Ollama + model

```bash
# Install Ollama from https://ollama.com, then:
ollama pull mistral
```

### 2. Backend

```bash
cd backend
pip install -r requirements.txt
copy .env.example .env   # optional
python main.py
```

Backend runs at **http://localhost:10000**

Check health: **http://localhost:10000/health**

### 3. Frontend

```bash
cd frontend
npm install
npm start
```

Frontend runs at **http://localhost:3000**

### 4. Chrome extension (Zoom capture)

1. Open Chrome → `chrome://extensions`
2. Enable **Developer mode**
3. **Load unpacked** → select `meet_extensiion` folder
4. Open a Zoom meeting tab → use extension popup

---

## How to use

### Option A — Upload `.txt` or audio

1. Open http://localhost:3000
2. Choose **Standalone** or **Connected** (+ Series ID)
3. Upload `.txt`, `.mp3`, or `.wav`
4. Click **Generate Summary**

### Option B — Zoom extension

1. Join Zoom in Chrome
2. Extension → **Start Transcription** → **Stop**
3. Open website → **Generate Zoom Meeting Summary** (no file needed)

### Option C — Connected meetings (RAG)

Use the same **Series ID** for related meetings, e.g. `sprint-12-standups`.

```bash
curl -X POST "http://localhost:10000/rag/query" \
  -H "Content-Type: application/json" \
  -d "{\"question\": \"Who owns the backend?\", \"series_id\": \"sprint-12-standups\"}"
```

---

## Meeting modes

| Mode | RAG | When to use |
|------|-----|-------------|
| **standalone** | Off | One-off unrelated meeting |
| **connected** | On (same series) | Recurring / project meetings |

---

## Project structure

```
backend/
  main.py              # FastAPI API
  config.py            # Local settings
  transcription/       # Whisper (free STT)
  llm/                 # Ollama (free LLM)
  rag/                 # ChromaDB RAG memory
frontend/              # React UI
meet_extensiion/       # Zoom Chrome extension
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Action items empty | Run `ollama pull mistral` and check `/health` |
| Audio upload fails | First run downloads Whisper model (~150MB for `base`) |
| Extension save fails | Backend must run on port **10000** |
| Slow first request | Models load on first use — normal |

---

## Cost

**$0** — no AssemblyAI, no OpenRouter, no Zoom Pro required.

---

## Deploy: Render (backend) + Vercel (frontend)

### 1. Render — backend

1. Push repo to GitHub
2. [Render Dashboard](https://dashboard.render.com) → **New → Blueprint** (or Web Service)
3. Connect repo — uses root `render.yaml`
4. Set environment variables:

| Variable | Example |
|----------|---------|
| `ALLOWED_ORIGINS` | `https://your-app.vercel.app,http://localhost:3000` |
| `FRONTEND_URL` | `https://your-app.vercel.app` |
| `ENV` | `production` |

5. Deploy → note URL: `https://your-app.onrender.com`

### 2. Vercel — frontend

1. [Vercel Dashboard](https://vercel.com) → **Import Project**
2. Root directory: **`frontend`**
3. Environment variable:

| Variable | Value |
|----------|-------|
| `REACT_APP_API_URL` | `https://your-app.onrender.com` |

4. Deploy → note URL: `https://your-app.vercel.app`

### 3. Extension (optional)

Edit `meet_extensiion/config.js`:

```javascript
BACKEND_URL: "https://your-app.onrender.com",
FRONTEND_URL: "https://your-app.vercel.app",
```

Reload extension in Chrome.

### Local vs deployed

| | Local | Render + Vercel |
|---|-------|-----------------|
| Frontend | `npm start` | Vercel URL |
| Backend | `python main.py` | Render URL |
| Ollama / Whisper | Works on laptop | **May not work on Render free tier** — use `.txt` upload for demo |
| Config | defaults | env vars + `config.js` |

**College demo tip:** Present locally for full AI features; deploy for UI + API + `.txt` upload.
