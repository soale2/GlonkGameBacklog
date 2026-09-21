"""Populate the local dev database with fake data, so the frontend can be built
against a realistic workspace before real Discord OAuth/bot wiring exists.

Usage: uv run python scripts/seed_dev_data.py
"""

from app.db import SessionLocal
from app.models import (
    BacklogEntry,
    BacklogStatus,
    Game,
    Recommendation,
    User,
    Workspace,
    WorkspaceMembership,
)

FAKE_GUILD_ID = "000000000000000001"

FAKE_USERS = [
    {"discord_id": "100000000000000001", "username": "alekar", "avatar_url": None},
    {"discord_id": "100000000000000002", "username": "glonk_friend", "avatar_url": None},
]

FAKE_GAMES = [
    {
        "external_id": 3498,
        "title": "Grand Theft Auto V",
        "cover_url": None,
        "release_date": "2013-09-17",
        "genres": "Action, Adventure",
        "platforms": "PC, PlayStation, Xbox",
    },
    {
        "external_id": 4200,
        "title": "Portal 2",
        "cover_url": None,
        "release_date": "2011-04-18",
        "genres": "Puzzle, Shooter",
        "platforms": "PC, PlayStation, Xbox",
    },
    {
        "external_id": 5286,
        "title": "Tunic",
        "cover_url": None,
        "release_date": "2022-03-16",
        "genres": "Adventure, Indie",
        "platforms": "PC, Xbox, Switch",
    },
]


def seed() -> None:
    db = SessionLocal()
    try:
        if db.query(Workspace).filter_by(discord_guild_id=FAKE_GUILD_ID).first():
            print("Dev workspace already seeded, skipping.")
            return

        workspace = Workspace(discord_guild_id=FAKE_GUILD_ID, name="Dev Test Server")
        db.add(workspace)
        db.flush()

        users = [User(**data) for data in FAKE_USERS]
        db.add_all(users)
        db.flush()

        for user in users:
            db.add(WorkspaceMembership(user_id=user.id, workspace_id=workspace.id))

        games = [Game(**data) for data in FAKE_GAMES]
        db.add_all(games)
        db.flush()

        db.add_all(
            [
                BacklogEntry(
                    user_id=users[0].id,
                    game_id=games[0].id,
                    status=BacklogStatus.COMPLETED,
                    rating=9,
                ),
                BacklogEntry(
                    user_id=users[0].id,
                    game_id=games[1].id,
                    status=BacklogStatus.PLAYING,
                ),
                BacklogEntry(
                    user_id=users[0].id,
                    game_id=games[2].id,
                    status=BacklogStatus.BACKLOG,
                ),
            ]
        )

        db.add(
            Recommendation(
                workspace_id=workspace.id,
                game_id=games[2].id,
                recommended_by_user_id=users[1].id,
                note="You'll love the art style, trust me",
                source="bot",
            )
        )

        db.commit()
        print(f"Seeded workspace {workspace.id} with {len(users)} users, {len(games)} games.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
