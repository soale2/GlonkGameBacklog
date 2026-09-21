from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.db import get_db
from app.models import ActivityEvent, User
from app.routers.backlog import _member_user_ids, _require_membership

router = APIRouter(prefix="/api/workspaces/{workspace_id}/activity", tags=["activity"])


def _serialize(event: ActivityEvent) -> dict:
    return {
        "id": event.id,
        "event_type": event.event_type,
        "from_status": event.from_status,
        "to_status": event.to_status,
        "created_at": event.created_at.isoformat(),
        "user": {"username": event.user.username, "avatar_url": event.user.avatar_url},
        "game": {"id": event.game.id, "title": event.game.title, "cover_url": event.game.cover_url},
    }


@router.get("")
def list_activity(
    workspace_id: int,
    limit: int = 30,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    _require_membership(db, user, workspace_id)
    events = (
        db.query(ActivityEvent)
        .filter(ActivityEvent.user_id.in_(_member_user_ids(db, workspace_id)))
        .order_by(ActivityEvent.created_at.desc())
        .limit(limit)
        .all()
    )
    return [_serialize(e) for e in events]
