"""make backlog entries and activity events user-global, not workspace-scoped

A user's status for a game should be the same fact everywhere they can see it, not
duplicated per Discord server. This drops workspace_id from both tables (rebuilding
them, since SQLite won't drop a column that's part of a FK/unique constraint) and
changes backlog_entries' uniqueness to (user_id, game_id). Existing rows are kept,
deduplicated by (user_id, game_id) if any workspace-scoped duplicates existed.

Revision ID: 442d0fe61107
Revises: db21ad9e976e
Create Date: 2026-09-21 16:08:27.794602

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '442d0fe61107'
down_revision: Union[str, Sequence[str], None] = 'db21ad9e976e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

backlog_status_enum = sa.Enum(
    'WISHLIST', 'BACKLOG', 'PLAYING', 'COMPLETED', 'DROPPED',
    name='backlogstatus',
    # The type already exists (created by the initial migration); this rebuild must not
    # try to CREATE TYPE it again when replayed against Postgres.
    create_type=False,
)


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'backlog_entries_new',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('game_id', sa.Integer(), nullable=False),
        sa.Column('status', backlog_status_enum, nullable=False),
        sa.Column('rating', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('hours_played', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['game_id'], ['games.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'game_id', name='uq_user_game'),
    )
    # Keep only the most recent row per (user_id, game_id) in case the same user had
    # entries for the same game logged under more than one workspace previously.
    op.execute(
        """
        INSERT INTO backlog_entries_new
            (id, user_id, game_id, status, rating, notes, hours_played, created_at, updated_at)
        SELECT id, user_id, game_id, status, rating, notes, hours_played, created_at, updated_at
        FROM backlog_entries
        WHERE id IN (SELECT MAX(id) FROM backlog_entries GROUP BY user_id, game_id)
        """
    )
    op.drop_table('backlog_entries')
    op.rename_table('backlog_entries_new', 'backlog_entries')

    op.create_table(
        'activity_events_new',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('game_id', sa.Integer(), nullable=False),
        sa.Column('event_type', sa.String(length=20), nullable=False),
        sa.Column('from_status', sa.String(length=20), nullable=True),
        sa.Column('to_status', sa.String(length=20), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['game_id'], ['games.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.execute(
        """
        INSERT INTO activity_events_new
            (id, user_id, game_id, event_type, from_status, to_status, created_at)
        SELECT id, user_id, game_id, event_type, from_status, to_status, created_at
        FROM activity_events
        """
    )
    op.drop_table('activity_events')
    op.rename_table('activity_events_new', 'activity_events')


def downgrade() -> None:
    """Downgrade schema. Best-effort only: workspace_id is added back nullable, since
    the original per-workspace association can no longer be reconstructed."""
    op.add_column('backlog_entries', sa.Column('workspace_id', sa.Integer(), nullable=True))
    op.add_column('activity_events', sa.Column('workspace_id', sa.Integer(), nullable=True))
