"""add activity_events table

Revision ID: db21ad9e976e
Revises: 75f608dde594
Create Date: 2026-09-21 15:57:29.217175

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'db21ad9e976e'
down_revision: Union[str, Sequence[str], None] = '75f608dde594'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('activity_events',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('workspace_id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('game_id', sa.Integer(), nullable=False),
    sa.Column('event_type', sa.String(length=20), nullable=False),
    sa.Column('from_status', sa.String(length=20), nullable=True),
    sa.Column('to_status', sa.String(length=20), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['game_id'], ['games.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # Also drops _alembic_tmp_games, a leftover scratch table SQLite's batch-mode table
    # rebuild left behind from an earlier (superseded) migration attempt on this table.
    op.execute("DROP TABLE IF EXISTS _alembic_tmp_games")


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('activity_events')
