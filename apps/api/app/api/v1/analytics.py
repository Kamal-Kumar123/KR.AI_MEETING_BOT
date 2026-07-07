from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.models import ActionItem, Meeting, User, get_db

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("")
def get_analytics(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    base = db.query(Meeting).filter(Meeting.user_id == user.id)
    total = base.count()
    ready = base.filter(Meeting.status == "ready").count()
    failed = base.filter(Meeting.status == "failed").count()
    favorites = base.filter(Meeting.is_favorite.is_(True)).count()
    total_duration = (
        db.query(func.coalesce(func.sum(Meeting.duration_seconds), 0))
        .filter(Meeting.user_id == user.id)
        .scalar()
    )

    platform_rows = (
        db.query(Meeting.platform, func.count(Meeting.id))
        .filter(Meeting.user_id == user.id)
        .group_by(Meeting.platform)
        .all()
    )
    action_items_count = (
        db.query(func.count(ActionItem.id))
        .join(Meeting, ActionItem.meeting_id == Meeting.id)
        .filter(Meeting.user_id == user.id)
        .scalar()
    )

    recent = (
        base.order_by(Meeting.created_at.desc()).limit(5).all()
    )

    return {
        "total_meetings": total,
        "ready_meetings": ready,
        "failed_meetings": failed,
        "favorite_meetings": favorites,
        "total_duration_seconds": int(total_duration or 0),
        "total_action_items": int(action_items_count or 0),
        "by_platform": {p: c for p, c in platform_rows},
        "recent_meetings": [
            {"id": m.id, "title": m.title, "status": m.status, "platform": m.platform, "created_at": m.created_at}
            for m in recent
        ],
    }
