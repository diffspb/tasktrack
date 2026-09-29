"""work packages — task assignment with immutable versions (FR-003, TT-09, ADR-020)

Revision ID: f7b5d2e9c3a1
Revises: e6a4c1d8b5f7
Create Date: 2026-09-30 10:00:00

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import Text
from sqlalchemy.dialects import postgresql

revision: str = 'f7b5d2e9c3a1'
down_revision: Union[str, Sequence[str], None] = 'e6a4c1d8b5f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('work_packages',
    sa.Column('task_id', sa.Uuid(), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.Column('content', postgresql.JSONB(astext_type=Text()), nullable=False),
    sa.Column('digest', sa.String(length=64), nullable=False),
    sa.Column('issued_by', sa.Uuid(), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['issued_by'], ['users.id'], ),
    sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('task_id', 'version')
    )
    op.create_index(op.f('ix_work_packages_task_id'), 'work_packages', ['task_id'], unique=False)
    op.add_column('tasks', sa.Column('work_package_draft', postgresql.JSONB(astext_type=Text()), nullable=True))
    op.add_column('tasks', sa.Column('work_package_version', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('tasks', 'work_package_version')
    op.drop_column('tasks', 'work_package_draft')
    op.drop_index(op.f('ix_work_packages_task_id'), table_name='work_packages')
    op.drop_table('work_packages')
