from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.db import get_db
from app.integrations.igdb import IgdbUnavailable, get_or_create_stub_game, match_steam_library
from app.integrations.steam import SteamError, fetch_owned_games
from app.models import BacklogEntry, BacklogStatus, Game, User
from app.routers.backlog import _require_membership

router = APIRouter(
    prefix="/api/workspaces/{workspace_id}/steam-import", tags=["steam-import"]
)


class PreviewRequest(BaseModel):
    profile: str


class CommitEntry(BaseModel):
    game_id: int | None = None
    title: str | None = None
    hours_played: float | None = None


class CommitRequest(BaseModel):
    entries: list[CommitEntry]


@router.post("/preview")
def preview_steam_import(
    workspace_id: int,
    payload: PreviewRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    _require_membership(db, user, workspace_id)

    try:
        _steam_id, display_name, owned_games = fetch_owned_games(payload.profile)
    except SteamError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        matches = match_steam_library(db, owned_games)
        db.commit()
    except IgdbUnavailable as exc:
        raise HTTPException(
            status_code=502, detail="Game details are not available right now. Try again later."
        ) from exc

    my_game_ids = {
        row[0] for row in db.query(BacklogEntry.game_id).filter_by(user_id=user.id).all()
    }

    items = []
    for pair in matches:
        steam_game = pair["steam_game"]
        game = pair["matched"]
        items.append(
            {
                "steam_appid": steam_game["appid"],
                "steam_name": steam_game.get("name") or f"App {steam_game['appid']}",
                "hours_played": round(steam_game.get("playtime_forever", 0) / 60, 1),
                "game": (
                    {"id": game.id, "title": game.title, "cover_url": game.cover_url}
                    if game
                    else None
                ),
                "already_in_backlog": game is not None and game.id in my_game_ids,
            }
        )

    items.sort(key=lambda item: item["hours_played"])
    return {"steam_display_name": display_name, "games": items}


@router.post("/commit")
def commit_steam_import(
    workspace_id: int,
    payload: CommitRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Bulk-adds the selected games to the caller's backlog as "backlog" status,
    with hours_played prefilled from Steam. Does not log individual activity events,
    since a dozens-of-games import would otherwise flood the workspace's feed."""
    _require_membership(db, user, workspace_id)

    imported = 0
    skipped = 0

    for entry in payload.entries:
        if entry.game_id is not None:
            game = db.get(Game, entry.game_id)
            if not game:
                skipped += 1
                continue
        elif entry.title:
            game = get_or_create_stub_game(db, entry.title)
        else:
            skipped += 1
            continue

        existing = db.query(BacklogEntry).filter_by(user_id=user.id, game_id=game.id).first()
        if existing:
            skipped += 1
            continue

        db.add(
            BacklogEntry(
                user_id=user.id,
                game_id=game.id,
                status=BacklogStatus.BACKLOG,
                hours_played=entry.hours_played,
            )
        )
        imported += 1

    db.commit()
    return {"imported": imported, "skipped": skipped}
