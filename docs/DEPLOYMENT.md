# Deployment Guide

## Local Development

No Postgres Docker needed. Use **SQLite** locally or **Neon** (free cloud PostgreSQL).

```bash
cd apps/api
cp .env.example .env
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
| `apps/web` | Vercel |
| `apps/api` | Railway / Render / Fly.io |
| Database | **Neon** (free PostgreSQL) or SQLite (local) |
| S3 | AWS S3 / Cloudflare R2 / MinIO |
| Ollama | Separate GPU/CPU server (not serverless) |

## Environment Variables

See `apps/api/.env.example` and set:

- `DATABASE_URL`
- `JWT_SECRET_KEY`
- `S3_*`
- `FRONTEND_URL`, `ALLOWED_ORIGINS`
- `OLLAMA_BASE_URL`, `OLLAMA_MODEL`

Web: `NEXT_PUBLIC_API_URL=https://api.yourdomain.com`

Extension: set API/Frontend URLs in Options page or `chrome.storage.sync`.

## CORS

Include:

- `https://yourdomain.com`
- `chrome-extension://<extension-id>`

## ML on Cloud

Free tiers **cannot** run Whisper + Ollama together. Options:

1. Hybrid: API in cloud, Ollama on a VPS
2. Replace Ollama with OpenAI/Anthropic API (backend only)
3. Use managed STT (Deepgram, AssemblyAI) for transcription
