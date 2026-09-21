from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.integrations.igdb import IgdbUnavailable, get_or_create_cached_game
from app.integrations.igdb import search_games as igdb_search

router = APIRouter(prefix="/api/games", tags=["games"])


def _serialize(game) -> dict:
    return {
        "id": game.id,
        "title": game.title,
        "cover_url": game.cover_url,
        "release_date": game.release_date,
        "genres": game.genres,
    }


@router.get("/search")
def search(q: str = Query(min_length=1), db: Session = Depends(get_db)) -> dict:
    try:
        results = igdb_search(q, limit=8)
    except IgdbUnavailable:
        return {"enriched": False, "results": []}

    games = [get_or_create_cached_game(db, r) for r in results]
    db.commit()
    return {"enriched": True, "results": [_serialize(g) for g in games]}
