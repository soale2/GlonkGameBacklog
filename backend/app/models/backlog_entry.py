import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base, utcnow

if TYPE_CHECKING:
    from app.models.game import Game
    from app.models.user import User


class BacklogStatus(str, enum.Enum):
    WISHLIST = "wishlist"
    BACKLOG = "backlog"
    PLAYING = "playing"
    COMPLETED = "completed"
    DROPPED = "dropped"


class BacklogEntry(Base):
    """One user's tracked status for one game. Not scoped to a workspace: it's the same
    fact regardless of which server's board you're viewing it from, so moving a game in
    one workspace is visible in every workspace you share it with."""

    __tablename__ = "backlog_entries"
    __table_args__ = (UniqueConstraint("user_id", "game_id", name="uq_user_game"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id"))
    status: Mapped[BacklogStatus] = mapped_column(
        Enum(BacklogStatus), default=BacklogStatus.BACKLOG
    )
    rating: Mapped[int | None] = mapped_column(default=None)
    notes: Mapped[str | None] = mapped_column(Text, default=None)
    hours_played: Mapped[float | None] = mapped_column(default=None)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)

    user: Mapped["User"] = relationship()
    game: Mapped["Game"] = relationship()
