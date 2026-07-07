from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.api.v1 import analytics, auth, meetings, recordings
from app.api.v1 import settings as settings_routes
from app.core.config import settings
from app.db.models import init_db

limiter = Limiter(key_func=get_remote_address, default_limits=[settings.rate_limit])


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="KRAI Meeting Assistant API",
    version="2.0.0",
    description="Production API for AI meeting recording, transcription, and insights.",
    lifespan=lifespan,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(recordings.router, prefix="/api/v1")
app.include_router(meetings.router, prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")
app.include_router(settings_routes.router, prefix="/api/v1")


@app.get("/health")
def health():
    from app.core.config import settings as cfg

    return {
        "status": "ok",
        "env": cfg.env,
        "version": "2.1.0",
        "celery": cfg.use_celery,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=settings.env == "local")
