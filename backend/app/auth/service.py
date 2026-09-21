from sqlalchemy.orm import Session

from app.models import User, Workspace, WorkspaceMembership


def sync_user_and_workspaces(db: Session, discord_user: dict, guilds: list[dict]) -> User:
    """Upsert the logged-in Discord user and auto-join them to any workspace whose
    guild they belong to (workspaces are only created by the bot on server invite)."""
    discord_id = discord_user["id"]
    avatar_hash = discord_user.get("avatar")
    avatar_url = (
        f"https://cdn.discordapp.com/avatars/{discord_id}/{avatar_hash}.png"
        if avatar_hash
        else None
    )
    username = discord_user.get("global_name") or discord_user["username"]

    user = db.query(User).filter_by(discord_id=discord_id).first()
    if user:
        user.username = username
        user.avatar_url = avatar_url
    else:
        user = User(discord_id=discord_id, username=username, avatar_url=avatar_url)
        db.add(user)
        db.flush()

    guild_ids = {g["id"] for g in guilds}
    matching_workspaces = (
        db.query(Workspace).filter(Workspace.discord_guild_id.in_(guild_ids)).all()
    )

    already_joined = {
        m.workspace_id for m in db.query(WorkspaceMembership).filter_by(user_id=user.id).all()
    }
    for workspace in matching_workspaces:
        if workspace.id not in already_joined:
            db.add(WorkspaceMembership(user_id=user.id, workspace_id=workspace.id))

    db.commit()
    return user
