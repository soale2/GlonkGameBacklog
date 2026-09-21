"""Discord bot process: workspace onboarding + lightweight slash commands.

Run separately from the web API: `uv run python -m bot.main`.
"""

import asyncio
import os

import discord
from aiohttp import web
from discord import app_commands

from app.config import get_settings
from app.db import SessionLocal
from app.models import Workspace
from bot.commands.recommend import handle_recommend

settings = get_settings()

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)


def ensure_workspace(guild: discord.Guild) -> None:
    db = SessionLocal()
    try:
        existing = db.query(Workspace).filter_by(discord_guild_id=str(guild.id)).first()
        if existing:
            return
        db.add(Workspace(discord_guild_id=str(guild.id), name=guild.name))
        db.commit()
        print(f"Provisioned workspace for guild: {guild.name} ({guild.id})")
    finally:
        db.close()


@client.event
async def on_ready() -> None:
    for guild in client.guilds:
        ensure_workspace(guild)
    await tree.sync()
    print(f"Bot logged in as {client.user} - in {len(client.guilds)} guild(s)")


@client.event
async def on_guild_join(guild: discord.Guild) -> None:
    ensure_workspace(guild)


@tree.command(name="recommend", description="Recommend a game to this server")
@app_commands.describe(game="Game title", note="The reason for your recommendation")
async def recommend(interaction: discord.Interaction, game: str, note: str | None = None) -> None:
    await handle_recommend(interaction, game, note)


async def _health(_request: web.Request) -> web.Response:
    return web.Response(text="ok")


async def _run_health_server() -> None:
    """A minimal HTTP server with nothing to do with Discord: some free hosts (Render)
    require a web process to bind a port, and an external keep-alive pinger (e.g.
    UptimeRobot) needs something to hit so the host doesn't let this process sleep and
    drop the bot's Discord connection. Harmless locally, just opens an unused port."""
    app = web.Application()
    app.router.add_get("/health", _health)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", "8080"))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()


async def _run() -> None:
    if not settings.discord_bot_token:
        raise SystemExit("DISCORD_BOT_TOKEN is not set in .env")
    async with client:
        await asyncio.gather(_run_health_server(), client.start(settings.discord_bot_token))


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
