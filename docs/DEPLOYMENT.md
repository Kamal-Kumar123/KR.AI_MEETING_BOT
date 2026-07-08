# Deployment Guide

## Local Development

No Postgres Docker needed. Use **SQLite** locally or **Neon** (free cloud PostgreSQL).

```bash
cd apps/api
cp .env.example .env
# Set DEEPGRAM_API_KEY and GEMINI_API_KEY in .env
pip install -r requirements.txt
python -m app.main
```

See [Neon Setup](NEON_SETUP.md) for free cloud database.

Optional infrastructure (MinIO + Redis only):

```bash
docker compose up -d
```

## Production Targets

| Component | Recommended Host |
|-----------|------------------|
| Frontend | Vercel / Netlify / Render static |
| `apps/api` | Railway / Render / Fly.io |
| Database | **Neon** (free PostgreSQL) or SQLite (local) |
| S3 | AWS S3 / Cloudflare R2 / MinIO |
| STT | **Deepgram** (cloud API) |
| LLM | **Google Gemini** (cloud API) |

## Environment Variables

See `apps/api/.env.example` and set:

- `DATABASE_URL`
- `JWT_SECRET_KEY`
- `S3_*`
- `FRONTEND_URL`, `ALLOWED_ORIGINS`
- `DEEPGRAM_API_KEY`, `DEEPGRAM_MODEL` (default: `nova-2`)
- `GEMINI_API_KEY`, `GEMINI_MODEL` (default: `gemini-2.0-flash`)
- `GOOGLE_CLIENT_ID`, `GOOGLE_EXTENSION_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`

Frontend: `REACT_APP_API_URL=https://api.yourdomain.com`

Extension: set API/Frontend URLs in Options page or `chrome.storage.sync`.

## Render

The repo includes `render.yaml` for the `apps/api` Docker service. On Render:

1. Create a **Web Service** from this repo (Docker, root `apps/api`).
2. Add `DEEPGRAM_API_KEY` and `GEMINI_API_KEY` in the Render dashboard (never commit keys).
3. Point `DATABASE_URL` at Neon (or Render Postgres).
4. Configure S3-compatible storage (R2 or AWS S3) — local MinIO is not available on Render.
5. Set `ALLOWED_ORIGINS` to your frontend URL and `chrome-extension://<extension-id>`.

Verify deployment: `GET /health` should return `"pipeline": "deepgram_gemini"` with `"deepgram": true` and `"gemini": true`.

No local Whisper or Ollama models are required — the API runs entirely on cloud STT/LLM.

## CORS

Include:

- `https://yourdomain.com`
- `chrome-extension://<extension-id>`

## RAG / Embeddings

ChromaDB and `all-MiniLM-L6-v2` embeddings run in-process on the API server. For persistent RAG across deploys, mount a volume or use a hosted ChromaDB instance.
