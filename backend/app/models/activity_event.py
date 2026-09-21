from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base, utcnow

if TYPE_CHECKING:
    from app.models.game import Game
    from app.models.user import User


class ActivityEvent(Base):
    """A log of backlog changes (added/status_changed/removed). Not workspace-scoped
    itself (it belongs to a user, same as BacklogEntry); a workspace's feed is whichever
    events belong to that workspace's members."""

    __tablename__ = "activity_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id"))
    event_type: Mapped[str] = mapped_column(String(20))  # "added" | "status_changed" | "removed"
    from_status: Mapped[str | None] = mapped_column(String(20), default=None)
    to_status: Mapped[str | None] = mapped_column(String(20), default=None)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    user: Mapped["User"] = relationship()
    game: Mapped["Game"] = relationship()
