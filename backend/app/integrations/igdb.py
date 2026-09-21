"""IGDB client with a local read-through cache.

IGDB auth rides on Twitch's client-credentials OAuth flow: exchange IGDB_CLIENT_ID +
IGDB_CLIENT_SECRET for a short-lived app access token, cache it in memory, then send
it with every IGDB query. This is a free-tier third party service and can still be
unreachable (bad credentials, outage, rate limit). Callers should treat IgdbUnavailable
as expected and fall back to get_or_create_stub_game, not as a hard failure.
"""

import difflib
import time

import httpx
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Game

TWITCH_TOKEN_URL = "https://id.twitch.tv/oauth2/token"
IGDB_GAMES_URL = "https://api.igdb.com/v4/games"
IGDB_EXTERNAL_GAMES_URL = "https://api.igdb.com/v4/external_games"
STEAM_EXTERNAL_GAME_SOURCE = 1

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


def get_game_by_external_id(db: Session, external_id: int) -> Game:
    """Fetch one exact game by its IGDB id (not a fuzzy search), for when the caller
    already knows exactly which game they want, e.g. picked from an autocomplete list."""
    existing = db.query(Game).filter_by(external_id=external_id).first()
    if existing:
        return existing

    settings = get_settings()
    if not settings.igdb_client_id or not settings.igdb_client_secret:
        raise IgdbUnavailable("IGDB_CLIENT_ID/IGDB_CLIENT_SECRET is not set")

    token = _get_access_token(settings.igdb_client_id, settings.igdb_client_secret)
    body = (
        f"where id = {external_id}; "
        "fields name,cover.image_id,first_release_date,genres.name,platforms.name; "
        "limit 1;"
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

    results = response.json()
    if not results:
        raise IgdbUnavailable(f"No IGDB game found for id {external_id}")

    return get_or_create_cached_game(db, results[0])


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


def _is_close_match(query: str, candidate: str) -> bool:
    """IGDB's search is fuzzy and always returns its best guess, even when nothing in
    its database is actually a good match (a title it simply doesn't have yet). Without
    this check, a search for a game IGDB has never heard of silently returns some
    unrelated game instead, with no way to tell the two cases apart."""
    query = query.strip().lower()
    candidate = candidate.strip().lower()
    if query in candidate or candidate in query:
        return True
    return difflib.SequenceMatcher(None, query, candidate).ratio() >= 0.6


def _chunks(items: list, size: int) -> list[list]:
    return [items[i : i + size] for i in range(0, len(items), size)]


def match_steam_appids(appids: list[int]) -> dict[int, int]:
    """Batch-resolve Steam App IDs to IGDB game IDs via IGDB's external_games table,
    an exact mapping IGDB itself maintains, rather than a fuzzy title search. Appids
    with no known IGDB mapping are simply absent from the returned dict."""
    if not appids:
        return {}

    settings = get_settings()
    if not settings.igdb_client_id or not settings.igdb_client_secret:
        raise IgdbUnavailable("IGDB_CLIENT_ID/IGDB_CLIENT_SECRET is not set")

    token = _get_access_token(settings.igdb_client_id, settings.igdb_client_secret)
    mapping: dict[int, int] = {}

    for chunk in _chunks(appids, 200):
        uid_list = ",".join(f'"{appid}"' for appid in chunk)
        body = (
            f"fields uid,game; "
            f"where uid = ({uid_list}) & external_game_source = {STEAM_EXTERNAL_GAME_SOURCE}; "
            "limit 500;"
        )
        try:
            response = httpx.post(
                IGDB_EXTERNAL_GAMES_URL,
                headers={
                    "Client-ID": settings.igdb_client_id,
                    "Authorization": f"Bearer {token}",
                },
                content=body,
                timeout=10.0,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise IgdbUnavailable(str(exc)) from exc

        for row in response.json():
            mapping[int(row["uid"])] = row["game"]

    return mapping


def get_or_create_cached_games_by_ids(db: Session, igdb_ids: list[int]) -> dict[int, Game]:
    """Batch version of get_game_by_external_id: reuses cached rows, fetches the rest
    from IGDB in chunks instead of one request per game."""
    unique_ids = list(dict.fromkeys(igdb_ids))
    result: dict[int, Game] = {}
    missing: list[int] = []

    for igdb_id in unique_ids:
        existing = db.query(Game).filter_by(external_id=igdb_id).first()
        if existing:
            result[igdb_id] = existing
        else:
            missing.append(igdb_id)

    if not missing:
        return result

    settings = get_settings()
    if not settings.igdb_client_id or not settings.igdb_client_secret:
        raise IgdbUnavailable("IGDB_CLIENT_ID/IGDB_CLIENT_SECRET is not set")
    token = _get_access_token(settings.igdb_client_id, settings.igdb_client_secret)

    for chunk in _chunks(missing, 200):
        id_list = ",".join(str(i) for i in chunk)
        body = (
            "fields name,cover.image_id,first_release_date,genres.name,platforms.name; "
            f"where id = ({id_list}); limit 500;"
        )
        try:
            response = httpx.post(
                IGDB_GAMES_URL,
                headers={
                    "Client-ID": settings.igdb_client_id,
                    "Authorization": f"Bearer {token}",
                },
                content=body,
                timeout=10.0,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise IgdbUnavailable(str(exc)) from exc

        for igdb_result in response.json():
            result[igdb_result["id"]] = get_or_create_cached_game(db, igdb_result)

    return result


def match_steam_library(db: Session, steam_games: list[dict]) -> list[dict]:
    """Pairs each Steam-owned game with its matched Game row, or None if IGDB has no
    Steam mapping for it. Two batched IGDB calls total (or fewer), not one per game."""
    appid_to_igdb = match_steam_appids([g["appid"] for g in steam_games])
    igdb_id_to_game = get_or_create_cached_games_by_ids(db, list(appid_to_igdb.values()))

    matched = []
    for steam_game in steam_games:
        igdb_id = appid_to_igdb.get(steam_game["appid"])
        game = igdb_id_to_game.get(igdb_id) if igdb_id is not None else None
        matched.append({"steam_game": steam_game, "matched": game})
    return matched


def resolve_game_by_title(db: Session, title: str) -> tuple[Game, bool]:
    """Best-effort lookup used by both the bot and the web API: try IGDB's top match,
    fall back to a stub game if IGDB is unavailable or has nothing close enough to this
    title. Returns (game, enriched)."""
    try:
        results = search_games(title, limit=1)
    except IgdbUnavailable:
        return get_or_create_stub_game(db, title), False

    if not results or not _is_close_match(title, results[0]["name"]):
        return get_or_create_stub_game(db, title), False

    return get_or_create_cached_game(db, results[0]), True
