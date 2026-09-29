"""project task_seq — atomic task numbering (FR-003, TT-03)

Revision ID: b7c1e2f4a901
Revises: 993840ac9a18
Create Date: 2026-09-29 12:00:00

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'b7c1e2f4a901'
down_revision: Union[str, Sequence[str], None] = '993840ac9a18'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'projects',
        sa.Column('task_seq', sa.Integer(), server_default='0', nullable=False),
    )
    # Continue numbering from the highest issued key (soft-deleted tasks included:
    # their keys stay taken). Project keys may contain '-', so parse the suffix only.
    op.execute(sa.text("""
        UPDATE projects p
        SET task_seq = GREATEST(p.task_seq, COALESCE((
            SELECT max(substring(t.key from '-([0-9]+)$')::int)
            FROM tasks t
            WHERE t.project_id = p.id
        ), 0))
    """))


def downgrade() -> None:
    op.drop_column('projects', 'task_seq')
