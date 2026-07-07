# KRAI Platform — Production Architecture

## Overview

```
extension/          Chrome MV3 (TypeScript) — record, upload, open report
apps/api/           FastAPI + PostgreSQL + S3 + AI pipeline
apps/web/           Next.js dashboard (TypeScript + Tailwind)
packages/shared/    Shared TypeScript types
docker-compose.yml  PostgreSQL + MinIO (local S3)
```

## Data Flow

1. User logs in via extension popup or web dashboard (JWT).
2. User joins Meet / Teams / Zoom **in Chrome**.
3. Extension captures **tab audio** (explicit consent + notification).
4. On stop → upload WebM to `POST /api/v1/recordings/upload`.
5. Backend stores file in S3, creates DB rows, runs background AI pipeline.
6. Frontend `/meeting/{id}` polls until `status=ready`.
7. User shares link using `share_token` (optional).

## AI Pipeline

| Step | Service |
|------|---------|
| Transcription | faster-whisper |
| Summaries | T5-small |
| Insights / action items | Ollama LLM |
| Vector memory (future) | ChromaDB (legacy backend) |

## Database Schema

- `users` — auth
- `meetings` — core entity + status machine
- `recordings` — S3 keys
- `transcripts` — full text + segments JSON
- `summaries` — executive/detailed + structured insights
- `action_items` — task, owner, deadline
- `participants` — optional metadata

## Meeting Status Machine

`detecting → recording → uploading → transcribing → processing → ready | failed`

## Security

- JWT on all private routes
- Share links require `share_token` query param
- Secrets in `.env` only
- Rate limiting via SlowAPI
- HTTPS required in production

## Extensibility

Add a new platform:

1. Add host pattern in `extension/src/lib/platforms.ts`
2. Add content script in `extension/src/content/{platform}.ts`
3. Register in `extension/manifest.json`

## Legacy Code

The original `backend/`, `frontend/`, and `meet_extensiion/` folders remain for your working college demo. New production code lives under `apps/` and `extension/`.
