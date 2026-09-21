from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base, utcnow

if TYPE_CHECKING:
    from app.models.recommendation import Recommendation
    from app.models.workspace_membership import WorkspaceMembership


class Workspace(Base):
    __tablename__ = "workspaces"

    id: Mapped[int] = mapped_column(primary_key=True)
    discord_guild_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    memberships: Mapped[list["WorkspaceMembership"]] = relationship(back_populates="workspace")
    recommendations: Mapped[list["Recommendation"]] = relationship(back_populates="workspace")
