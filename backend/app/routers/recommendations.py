from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.db import get_db
from app.integrations.igdb import resolve_game_by_title
from app.models import ActivityEvent, BacklogEntry, BacklogStatus, Game, Recommendation, User
from app.routers.backlog import _require_membership

router = APIRouter(prefix="/api/workspaces/{workspace_id}/recommendations", tags=["recommendations"])


class CreateRecommendation(BaseModel):
    game_id: int | None = None
    title: str | None = None
    note: str | None = None


def _serialize(rec: Recommendation) -> dict:
    return {
        "id": rec.id,
        "note": rec.note,
        "source": rec.source,
        "created_at": rec.created_at.isoformat(),
        "recommended_by": {
            "id": rec.recommended_by.id,
            "username": rec.recommended_by.username,
            "avatar_url": rec.recommended_by.avatar_url,
        },
        "game": {
            "id": rec.game.id,
            "title": rec.game.title,
            "cover_url": rec.game.cover_url,
            "release_date": rec.game.release_date,
            "genres": rec.game.genres,
        },
    }


@router.get("")
def list_recommendations(
    workspace_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    _require_membership(db, user, workspace_id)
    recs = (
        db.query(Recommendation)
        .filter_by(workspace_id=workspace_id)
        .order_by(Recommendation.created_at.desc())
        .all()
    )
    return [_serialize(r) for r in recs]


@router.post("")
def create_recommendation(
    workspace_id: int,
    payload: CreateRecommendation,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    _require_membership(db, user, workspace_id)

    if payload.game_id is not None:
        game = db.get(Game, payload.game_id)
        if not game:
            raise HTTPException(status_code=404, detail="This game could not be found.")
    elif payload.title:
        game, _ = resolve_game_by_title(db, payload.title)
    else:
        raise HTTPException(status_code=400, detail="Choose a game to recommend.")

    rec = Recommendation(
        workspace_id=workspace_id,
        game_id=game.id,
        recommended_by_user_id=user.id,
        note=payload.note,
        source="web",
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return _serialize(rec)


@router.post("/{recommendation_id}/accept")
def accept_recommendation(
    workspace_id: int,
    recommendation_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Add a recommended game to the caller's own backlog. Does not remove the
    recommendation, so it still shows who suggested it to the whole workspace."""
    _require_membership(db, user, workspace_id)
    rec = db.query(Recommendation).filter_by(id=recommendation_id, workspace_id=workspace_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail="This recommendation could not be found.")

    existing = db.query(BacklogEntry).filter_by(user_id=user.id, game_id=rec.game_id).first()
    if existing:
        raise HTTPException(status_code=409, detail="This game is already in your backlog.")

    entry = BacklogEntry(user_id=user.id, game_id=rec.game_id, status=BacklogStatus.BACKLOG)
    db.add(entry)
    db.flush()
    db.add(
        ActivityEvent(
            user_id=user.id,
            game_id=rec.game_id,
            event_type="added",
            to_status=BacklogStatus.BACKLOG.value,
        )
    )
    db.commit()
    db.refresh(entry)
    return {"id": entry.id, "status": entry.status.value}
