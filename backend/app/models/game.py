from datetime import datetime

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base, utcnow


class Game(Base):
    """Read-through cache of IGDB metadata, keyed by IGDB's game id."""

    __tablename__ = "games"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Nullable: a game can start as a title-only stub (e.g. IGDB was unreachable when it was
    # added) and get enriched with an external_id + metadata later once a lookup succeeds.
    external_id: Mapped[int | None] = mapped_column(unique=True, index=True, default=None)
    title: Mapped[str] = mapped_column(String(255))
    cover_url: Mapped[str | None] = mapped_column(String(500), default=None)
    release_date: Mapped[str | None] = mapped_column(String(20), default=None)
    genres: Mapped[str | None] = mapped_column(String(255), default=None)
    platforms: Mapped[str | None] = mapped_column(String(255), default=None)
    cached_at: Mapped[datetime] = mapped_column(default=utcnow)
