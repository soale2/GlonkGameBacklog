"""rename games.rawg_id to external_id

Revision ID: 75f608dde594
Revises: cfd83b04fe95
Create Date: 2026-09-21 15:21:13.764766

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '75f608dde594'
down_revision: Union[str, Sequence[str], None] = 'cfd83b04fe95'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema. Plain SQL (valid on both SQLite 3.25+ and Postgres) instead of
    batch mode, which mishandles the unique index during this particular rename."""
    op.execute("ALTER TABLE games RENAME COLUMN rawg_id TO external_id")
    op.execute("DROP INDEX ix_games_rawg_id")
    op.execute("CREATE UNIQUE INDEX ix_games_external_id ON games (external_id)")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("ALTER TABLE games RENAME COLUMN external_id TO rawg_id")
    op.execute("DROP INDEX ix_games_external_id")
    op.execute("CREATE UNIQUE INDEX ix_games_rawg_id ON games (rawg_id)")
