"""Steam Web API client: resolve a profile to a SteamID64, then read its public
game library. Uses one app-wide Steam API key (free, from
https://steamcommunity.com/dev/apikey), not a per-user login: Steam's ownership data
for a profile is readable by any key as long as that profile's "Game details" privacy
setting is Public.
"""

import re

import httpx

from app.config import get_settings

RESOLVE_VANITY_URL = "https://api.steampowered.com/ISteamUser/ResolveVanityURL/v0001/"
OWNED_GAMES_URL = "https://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/"
PLAYER_SUMMARIES_URL = "https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/"

_STEAM_ID64_RE = re.compile(r"^\d{17}$")
_PROFILE_ID_RE = re.compile(r"steamcommunity\.com/profiles/(\d{17})")
_VANITY_URL_RE = re.compile(r"steamcommunity\.com/id/([^/]+)")


class SteamError(Exception):
    """Base class. The message is written to be shown to the user directly."""


class SteamUnavailable(SteamError):
    """Steam's API could not be reached, or STEAM_API_KEY is not configured."""


class SteamProfileNotFound(SteamError):
    """The given profile URL, vanity name, or SteamID64 does not match a real account."""


class SteamLibraryPrivate(SteamError):
    """The profile exists, but its game list is not public."""


def _extract_identifier(raw: str) -> tuple[str, bool]:
    """Returns (identifier, is_already_a_steamid64)."""
    raw = raw.strip().rstrip("/")
    if match := _PROFILE_ID_RE.search(raw):
        return match.group(1), True
    if match := _VANITY_URL_RE.search(raw):
        return match.group(1), False
    if _STEAM_ID64_RE.fullmatch(raw):
        return raw, True
    return raw, False


def resolve_steam_id(raw: str) -> str:
    """Accepts a full profile URL, a vanity URL, a bare vanity name, or a raw
    SteamID64, and returns a SteamID64."""
    identifier, is_id = _extract_identifier(raw)
    if is_id:
        return identifier

    settings = get_settings()
    if not settings.steam_api_key:
        raise SteamUnavailable("STEAM_API_KEY is not set")

    try:
        response = httpx.get(
            RESOLVE_VANITY_URL,
            params={"key": settings.steam_api_key, "vanityurl": identifier},
            timeout=5.0,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise SteamUnavailable(str(exc)) from exc

    data = response.json().get("response", {})
    if data.get("success") != 1:
        raise SteamProfileNotFound(f'No Steam profile found for "{raw}".')
    return data["steamid"]


def get_owned_games(steam_id: str) -> list[dict]:
    settings = get_settings()
    if not settings.steam_api_key:
        raise SteamUnavailable("STEAM_API_KEY is not set")

    try:
        response = httpx.get(
            OWNED_GAMES_URL,
            params={
                "key": settings.steam_api_key,
                "steamid": steam_id,
                "format": "json",
                "include_appinfo": 1,
                "include_played_free_games": 1,
            },
            timeout=10.0,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise SteamUnavailable(str(exc)) from exc

    games = response.json().get("response", {}).get("games")
    if games is None:
        raise SteamLibraryPrivate(
            "This Steam library is private. In Steam, go to Privacy Settings and set "
            '"Game details" to Public, then try again.'
        )
    return games


def get_player_name(steam_id: str) -> str | None:
    """Best-effort display name for the profile being imported. Returns None on any
    failure rather than raising, since this is only used for a friendly confirmation
    message and should never block an import."""
    settings = get_settings()
    if not settings.steam_api_key:
        return None
    try:
        response = httpx.get(
            PLAYER_SUMMARIES_URL,
            params={"key": settings.steam_api_key, "steamids": steam_id},
            timeout=5.0,
        )
        response.raise_for_status()
        players = response.json().get("response", {}).get("players", [])
        return players[0]["personaname"] if players else None
    except (httpx.HTTPError, KeyError, IndexError):
        return None


def fetch_owned_games(raw_identifier: str) -> tuple[str, str | None, list[dict]]:
    """Returns (steam_id, display_name, owned_games)."""
    steam_id = resolve_steam_id(raw_identifier)
    games = get_owned_games(steam_id)
    name = get_player_name(steam_id)
    return steam_id, name, games
