from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.db import get_db
from app.integrations.igdb import resolve_game_by_title
from app.models import ActivityEvent, BacklogEntry, BacklogStatus, Game, User, WorkspaceMembership

router = APIRouter(prefix="/api/workspaces/{workspace_id}/backlog", tags=["backlog"])


class CreateBacklogEntry(BaseModel):
    game_id: int | None = None
    title: str | None = None
    status: BacklogStatus = BacklogStatus.BACKLOG


class UpdateBacklogEntry(BaseModel):
    status: BacklogStatus | None = None
    rating: int | None = None
    notes: str | None = None
    hours_played: float | None = None


def _require_membership(db: Session, user: User, workspace_id: int) -> None:
    membership = (
        db.query(WorkspaceMembership)
        .filter_by(user_id=user.id, workspace_id=workspace_id)
        .first()
    )
    if not membership:
        raise HTTPException(status_code=403, detail="You are not a member of this server.")


def _member_user_ids(db: Session, workspace_id: int) -> list[int]:
    rows = db.query(WorkspaceMembership.user_id).filter_by(workspace_id=workspace_id).all()
    return [row[0] for row in rows]


def _serialize(entry: BacklogEntry) -> dict:
    return {
        "id": entry.id,
        "status": entry.status.value,
        "rating": entry.rating,
        "notes": entry.notes,
        "hours_played": entry.hours_played,
        "user": {
            "id": entry.user.id,
            "username": entry.user.username,
            "avatar_url": entry.user.avatar_url,
        },
        "game": {
            "id": entry.game.id,
            "title": entry.game.title,
            "cover_url": entry.game.cover_url,
            "release_date": entry.game.release_date,
            "genres": entry.game.genres,
        },
    }


@router.get("")
def list_entries(
    workspace_id: int,
    status: BacklogStatus | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    """Every member's entries, not just the caller's, so the board can show who else has
    a given game. An entry itself isn't tied to a workspace: this just shows whichever
    entries belong to this workspace's current members."""
    _require_membership(db, user, workspace_id)
    query = db.query(BacklogEntry).filter(
        BacklogEntry.user_id.in_(_member_user_ids(db, workspace_id))
    )
    if status:
        query = query.filter_by(status=status)
    return [_serialize(e) for e in query.all()]


@router.post("")
def create_entry(
    workspace_id: int,
    payload: CreateBacklogEntry,
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
        raise HTTPException(status_code=400, detail="Choose a game to add.")

    existing = db.query(BacklogEntry).filter_by(user_id=user.id, game_id=game.id).first()
    if existing:
        raise HTTPException(status_code=409, detail="This game is already in your backlog.")

    entry = BacklogEntry(user_id=user.id, game_id=game.id, status=payload.status)
    db.add(entry)
    db.flush()
    db.add(
        ActivityEvent(
            user_id=user.id,
            game_id=game.id,
            event_type="added",
            to_status=payload.status.value,
        )
    )
    db.commit()
    db.refresh(entry)
    return _serialize(entry)


@router.patch("/{entry_id}")
def update_entry(
    workspace_id: int,
    entry_id: int,
    payload: UpdateBacklogEntry,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    _require_membership(db, user, workspace_id)
    entry = db.query(BacklogEntry).filter_by(id=entry_id, user_id=user.id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="This game is not in your backlog.")

    updates = payload.model_dump(exclude_unset=True)
    previous_status = entry.status

    for field, value in updates.items():
        setattr(entry, field, value)

    if "status" in updates and entry.status != previous_status:
        db.add(
            ActivityEvent(
                user_id=user.id,
                game_id=entry.game_id,
                event_type="status_changed",
                from_status=previous_status.value,
                to_status=entry.status.value,
            )
        )

    db.commit()
    db.refresh(entry)
    return _serialize(entry)


@router.delete("/{entry_id}", status_code=204)
def delete_entry(
    workspace_id: int,
    entry_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    _require_membership(db, user, workspace_id)
    entry = db.query(BacklogEntry).filter_by(id=entry_id, user_id=user.id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="This game is not in your backlog.")

    db.add(
        ActivityEvent(
            user_id=user.id,
            game_id=entry.game_id,
            event_type="removed",
            from_status=entry.status.value,
        )
    )
    db.delete(entry)
    db.commit()
