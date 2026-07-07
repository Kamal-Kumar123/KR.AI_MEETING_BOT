# Neon Database Setup (Free PostgreSQL)

Neon **is** PostgreSQL — free tier, no local Docker needed. Our app already works with it; you only change `DATABASE_URL`.

## 1. Create Neon account

1. Go to [https://neon.tech](https://neon.tech)
2. Sign up (free)
3. Create a new project (e.g. `krai-meetings`)

## 2. Copy connection string

In Neon dashboard → **Connection details** → copy the **pooled** or **direct** connection string.

It looks like:

```
postgresql://neondb_owner:xxxxxxxx@ep-cool-name-12345678.us-east-2.aws.neon.tech/neondb?sslmode=require
```

## 3. Add to backend `.env`

```bash
cd apps/api
cp .env.example .env
```

Edit `apps/api/.env`:

```env
DATABASE_URL=postgresql://neondb_owner:YOUR_PASSWORD@ep-xxxx.aws.neon.tech/neondb?sslmode=require
ENV=production
```

Comment out or remove the SQLite line if you switch fully to Neon.

## 4. Start API — tables auto-create

```bash
pip install -r requirements.txt
python -m app.main
```

On first startup, SQLAlchemy creates all tables in Neon.

## 5. Verify

- http://localhost:8000/health → `status: ok`
- Register at http://localhost:3000/login
- Data is stored in Neon (check Neon dashboard → Tables)

## Local vs Neon

| | SQLite (local) | Neon (cloud) |
|---|----------------|--------------|
| Cost | Free | Free tier |
| Docker | Not needed | Not needed |
| Best for | Quick laptop dev | Deploy, share DB, extension demo |
| Connection | `sqlite:///./krai_local.db` | `postgresql://...@neon.tech/...` |

## Notes

- **Do not commit** `.env` — it contains your Neon password.
- Neon free tier has storage/compute limits — fine for college project.
- You can drop Docker Postgres entirely — `docker compose` is optional now (MinIO/Redis only if needed).

## Troubleshooting

| Error | Fix |
|-------|-----|
| `Connection refused` | Wrong `DATABASE_URL` or Neon project paused — wake it in dashboard |
| `SSL required` | Add `?sslmode=require` to URL |
| `password authentication failed` | Reset password in Neon → update `.env` |
