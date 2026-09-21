from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base, utcnow

if TYPE_CHECKING:
    from app.models.game import Game
    from app.models.user import User
    from app.models.workspace import Workspace


class Recommendation(Base):
    """A game tagged as 'recommended by [friend]' for a workspace, from the web app or the bot."""

    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(primary_key=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"))
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id"))
    recommended_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    note: Mapped[str | None] = mapped_column(Text, default=None)
    source: Mapped[str] = mapped_column(String(10), default="web")  # "web" or "bot"
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    workspace: Mapped["Workspace"] = relationship(back_populates="recommendations")
    game: Mapped["Game"] = relationship()
    recommended_by: Mapped["User"] = relationship()
