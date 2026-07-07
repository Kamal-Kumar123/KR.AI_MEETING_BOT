from app.worker.celery_app import celery_app
from app.services.ai_pipeline import process_meeting_pipeline
from app.db.models import SessionLocal


@celery_app.task(name="process_meeting", bind=True, max_retries=2)
def process_meeting_task(self, meeting_id: str) -> dict:
    db = SessionLocal()
    try:
        process_meeting_pipeline(db, meeting_id)
        return {"meeting_id": meeting_id, "status": "completed"}
    except Exception as exc:
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=30)
        raise
    finally:
        db.close()


def enqueue_meeting_pipeline(meeting_id: str) -> str:
    """Dispatch to Celery if enabled, else run synchronously in a thread."""
    from app.core.config import settings
    import threading

    if settings.use_celery:
        result = process_meeting_task.delay(meeting_id)
        return result.id

    thread = threading.Thread(target=_run_sync, args=(meeting_id,), daemon=True)
    thread.start()
    return "sync"


def _run_sync(meeting_id: str) -> None:
    db = SessionLocal()
    try:
        process_meeting_pipeline(db, meeting_id)
    finally:
        db.close()
