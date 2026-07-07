# Phase 2 — Extension Developer Mode Test Guide

## 1. Start infrastructure

```bash
docker compose up -d
```

Starts PostgreSQL, Redis, MinIO. Optional Celery worker:

```bash
docker compose up celery-worker -d
```

## 2. Configure API

```bash
cd apps/api
cp .env.example .env
# Set USE_CELERY=true if Redis is running
pip install -r requirements.txt
python -m app.main
```

## 3. Configure Web

```bash
cd apps/web
cp .env.example .env.local
npm install
npm run dev
```

## 4. Build extension

```bash
cd extension
npm install
npm run build
```

Edit `extension/manifest.json` → set `oauth2.client_id` to your Google OAuth client ID (Chrome extension type).

## 5. Load in Chrome

1. `chrome://extensions` → Developer mode ON
2. **Load unpacked** → select `extension/dist`
3. Pin the extension

## 6. Test flow

1. Register at http://localhost:3000/login (or login in extension popup)
2. Open https://meet.google.com (or Teams/Zoom web)
3. Extension popup → **Start Recording** (allow tab audio)
4. Speak or play audio → **Stop & Upload**
5. Meeting report opens at `/meeting/{id}` with live status updates
6. When `ready` → **Export PDF**, **Copy Summary**
7. Check **Analytics** and **Settings** in dashboard nav

## 7. Google Login (optional)

- Create OAuth client in Google Cloud Console
- Web: add `NEXT_PUBLIC_GOOGLE_CLIENT_ID` to `apps/web/.env.local`
- Extension: set `oauth2.client_id` in manifest + authorized redirect from `chrome.identity.getRedirectURL()`

## 8. Run tests

```bash
# API
cd apps/api && pytest

# Web E2E (needs dev server)
cd apps/web && npx playwright install chromium && npm run test:e2e
```

## Permissions reminder

Recording always shows a Chrome notification. Users must explicitly start recording — never silent capture.
