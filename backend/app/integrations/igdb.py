"""IGDB client with a local read-through cache.

IGDB auth rides on Twitch's client-credentials OAuth flow: exchange IGDB_CLIENT_ID +
IGDB_CLIENT_SECRET for a short-lived app access token, cache it in memory, then send
it with every IGDB query. This is a free-tier third party service and can still be
unreachable (bad credentials, outage, rate limit). Callers should treat IgdbUnavailable
as expected and fall back to get_or_create_stub_game, not as a hard failure.
"""

import time

import httpx
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Game

TWITCH_TOKEN_URL = "https://id.twitch.tv/oauth2/token"
IGDB_GAMES_URL = "https://api.igdb.com/v4/games"

_token_cache: dict[str, float | str] = {}


class IgdbUnavailable(Exception):
    """Raised when IGDB can't be reached or returns an error (missing key, outage, rate limit)."""


def _get_access_token(client_id: str, client_secret: str) -> str:
    cached_token = _token_cache.get("token")
    expires_at = _token_cache.get("expires_at", 0.0)
    if cached_token and time.time() < expires_at:
        return str(cached_token)

    try:
        response = httpx.post(
            TWITCH_TOKEN_URL,
            params={
                "client_id": client_id,
                "client_secret": client_secret,
                "grant_type": "client_credentials",
            },
            timeout=5.0,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise IgdbUnavailable(str(exc)) from exc

    data = response.json()
    _token_cache["token"] = data["access_token"]
    _token_cache["expires_at"] = time.time() + data["expires_in"] - 60
    return data["access_token"]


def search_games(query: str, limit: int = 5) -> list[dict]:
    settings = get_settings()
    if not settings.igdb_client_id or not settings.igdb_client_secret:
        raise IgdbUnavailable("IGDB_CLIENT_ID/IGDB_CLIENT_SECRET is not set")

    token = _get_access_token(settings.igdb_client_id, settings.igdb_client_secret)

    body = (
        f'search "{query}"; '
        "fields name,cover.image_id,first_release_date,genres.name,platforms.name; "
        f"limit {limit};"
    )
    try:
        response = httpx.post(
            IGDB_GAMES_URL,
            headers={
                "Client-ID": settings.igdb_client_id,
                "Authorization": f"Bearer {token}",
            },
            content=body,
            timeout=5.0,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise IgdbUnavailable(str(exc)) from exc

    return response.json()


def _cover_url(igdb_result: dict) -> str | None:
    image_id = igdb_result.get("cover", {}).get("image_id")
    if not image_id:
        return None
    return f"https://images.igdb.com/igdb/image/upload/t_cover_big/{image_id}.jpg"


def _release_date(igdb_result: dict) -> str | None:
    timestamp = igdb_result.get("first_release_date")
    if not timestamp:
        return None
    return time.strftime("%Y-%m-%d", time.gmtime(timestamp))


def get_or_create_cached_game(db: Session, igdb_result: dict) -> Game:
    """Read-through cache: reuse an existing row for this external_id, or create one."""
    external_id = igdb_result["id"]
    existing = db.query(Game).filter_by(external_id=external_id).first()
    if existing:
        return existing

    game = Game(
        external_id=external_id,
        title=igdb_result["name"],
        cover_url=_cover_url(igdb_result),
        release_date=_release_date(igdb_result),
        genres=", ".join(g["name"] for g in igdb_result.get("genres", [])) or None,
        platforms=", ".join(p["name"] for p in igdb_result.get("platforms", [])) or None,
    )
    db.add(game)
    db.flush()
    return game


def get_or_create_stub_game(db: Session, title: str) -> Game:
    """Fallback when IGDB is unavailable: a title-only Game row, matched case-insensitively
    on repeat lookups so we don't create duplicates while IGDB stays down."""
    existing = db.query(Game).filter(Game.external_id.is_(None), Game.title.ilike(title)).first()
    if existing:
        return existing

    game = Game(external_id=None, title=title)
    db.add(game)
    db.flush()
    return game


def resolve_game_by_title(db: Session, title: str) -> tuple[Game, bool]:
    """Best-effort lookup used by both the bot and the web API: try IGDB's top match,
    fall back to a stub game if IGDB is unavailable. Returns (game, enriched)."""
    try:
        results = search_games(title, limit=1)
    except IgdbUnavailable:
        return get_or_create_stub_game(db, title), False

    if not results:
        return get_or_create_stub_game(db, title), False

    return get_or_create_cached_game(db, results[0]), True
