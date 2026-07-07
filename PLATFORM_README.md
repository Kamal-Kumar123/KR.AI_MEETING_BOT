# KRAI Meeting Assistant — Platform v2

Production-ready AI meeting assistant: Chrome Extension + FastAPI + Next.js + **Neon DB** + S3.

## Quick Start (no Docker required)

```bash
cd apps/api && cp .env.example .env && pip install -r requirements.txt && python -m app.main
cd apps/web && npm install && npm run dev
cd extension && npm install && npm run build
```

**Database options:**
- **Local:** SQLite (default) — `DATABASE_URL=sqlite:///./krai_local.db`
- **Cloud (free):** [Neon PostgreSQL](docs/NEON_SETUP.md) — paste connection string in `.env`

Optional: `docker compose up -d` for Redis + MinIO only.

- API: http://localhost:8000/health
- Web: http://localhost:3000
- Extension: Load `extension/dist` in Chrome

## Project Layout

```
apps/api/       FastAPI backend (Neon / SQLite, S3, JWT, AI pipeline)
apps/web/       Next.js dashboard
extension/      Chrome MV3 TypeScript extension
packages/shared Shared types
docs/           Architecture, API, deployment, Chrome Store guides
backend/        Legacy v1 demo (still works locally)
frontend/       Legacy CRA demo
meet_extensiion/ Legacy extension
```

## Docs

- [Neon DB Setup](docs/NEON_SETUP.md)
- [Architecture](docs/ARCHITECTURE.md)
- [API](docs/API.md)
- [Deployment](docs/DEPLOYMENT.md)
- [Chrome Web Store](docs/CHROME_STORE.md)
- [Privacy Policy template](docs/PRIVACY_POLICY.md)

## Implemented in v2

- JWT auth (register/login)
- Meeting CRUD + share tokens
- S3 recording upload
- Whisper transcription + T5 + Ollama insights
- Extension tab audio capture (Meet, Teams, Zoom web)
- Auto-open meeting report page with polling UI

## Implemented in v2.1 (Phase 2)

- Google OAuth (web GIS + extension `chrome.identity`)
- PDF export (`GET /meeting/{id}/export/pdf`)
- Analytics dashboard (`/analytics`)
- Full settings UI (web `/settings` + extension options page)
- Celery + Redis queue for long meeting processing (`USE_CELERY=true`)
- Playwright E2E smoke tests + expanded pytest suite
- Real branding icons in `extension/icons/`

## Run tests

```bash
cd apps/api && pytest
cd apps/web && npm run test:e2e
```

See [Extension Dev Test Guide](docs/EXTENSION_DEV_TEST.md) before loading in Chrome.

## Roadmap (Phase 3)

- Celery on production with autoscaling
- Google OAuth token refresh
- PDF styling + charts in analytics
- Playwright extension flow automation
