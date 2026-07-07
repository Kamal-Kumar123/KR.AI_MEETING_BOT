# API Reference (v1)

Base URL: `http://localhost:8000`

## Auth

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/auth/register` | `{ email, password, full_name? }` |
| POST | `/api/v1/auth/login` | `{ email, password }` → JWT |
| POST | `/api/v1/auth/google` | Stub — configure OAuth in production |
| POST | `/api/v1/auth/logout` | Client-side token delete |
| POST | `/api/v1/auth/forgot-password` | Stub |

## Recordings

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/recordings/upload` | Multipart: `file`, `meeting_id?`, `platform`, `meeting_url` |

## Meetings

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/meetings` | Create meeting session |
| GET | `/api/v1/meetings` | List + search `?q=&tag=&favorite=` |
| GET | `/api/v1/meeting/{id}` | Details; public with `?share={share_token}` |
| PATCH | `/api/v1/meeting/{id}` | Update title, tags, favorite |
| DELETE | `/api/v1/meeting/{id}` | Delete meeting + S3 object |
| POST | `/api/v1/transcribe` | Re-run transcription pipeline |
| POST | `/api/v1/generate-summary` | Regenerate AI insights |

## Health

| GET | `/health` |

All protected routes: `Authorization: Bearer <token>`
