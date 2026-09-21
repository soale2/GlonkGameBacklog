import discord

from app.db import SessionLocal
from app.integrations.igdb import IgdbUnavailable, get_game_by_external_id, resolve_game_by_title
from app.models import Recommendation, User, Workspace


def upsert_user(db, discord_user: discord.User | discord.Member) -> User:
    user = db.query(User).filter_by(discord_id=str(discord_user.id)).first()
    avatar_url = discord_user.display_avatar.url if discord_user.display_avatar else None
    if user:
        user.username = str(discord_user)
        user.avatar_url = avatar_url
        return user

    user = User(discord_id=str(discord_user.id), username=str(discord_user), avatar_url=avatar_url)
    db.add(user)
    db.flush()
    return user


async def handle_recommend(
    interaction: discord.Interaction, game: str, note: str | None = None
) -> None:
    if interaction.guild is None:
        await interaction.response.send_message(
            "This command works only in a server. It does not work in a direct message.",
            ephemeral=True,
        )
        return

    await interaction.response.defer()

    db = SessionLocal()
    try:
        workspace = db.query(Workspace).filter_by(discord_guild_id=str(interaction.guild.id)).first()
        if workspace is None:
            await interaction.followup.send(
                "This server is not set up yet. Remove the bot and add it again."
            )
            return

        recommender = upsert_user(db, interaction.user)

        # A numeric value means the user picked a suggestion from the autocomplete list,
        # so we fetch that exact game instead of running a fresh fuzzy search on its title
        # (which can rank a different, more obscure game above the one they picked).
        if game.strip().isdigit():
            try:
                game_row = get_game_by_external_id(db, int(game.strip()))
                enriched = True
            except IgdbUnavailable:
                game_row, enriched = resolve_game_by_title(db, game)
        else:
            game_row, enriched = resolve_game_by_title(db, game)

        recommendation = Recommendation(
            workspace_id=workspace.id,
            game_id=game_row.id,
            recommended_by_user_id=recommender.id,
            note=note,
            source="bot",
        )
        db.add(recommendation)
        db.commit()

        embed = discord.Embed(
            title=f"Recommended: {game_row.title}",
            description=note or None,
        )
        embed.set_footer(text=f"Recommended by {interaction.user.display_name}")
        if not enriched:
            embed.add_field(
                name="Note",
                value="Game details are not available right now. This was added by title only.",
                inline=False,
            )
        if game_row.cover_url:
            embed.set_thumbnail(url=game_row.cover_url)

        await interaction.followup.send(embed=embed)
    finally:
        db.close()
