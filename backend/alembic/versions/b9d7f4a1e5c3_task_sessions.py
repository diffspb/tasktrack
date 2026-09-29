"""task sessions and checkpoints (FR-003, TT-12, ADR-022)

Revision ID: b9d7f4a1e5c3
Revises: a8c6e3f0d4b2
Create Date: 2026-09-30 14:00:00

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import Text
from sqlalchemy.dialects import postgresql

revision: str = 'b9d7f4a1e5c3'
down_revision: Union[str, Sequence[str], None] = 'a8c6e3f0d4b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('task_sessions',
    sa.Column('task_id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('work_package_id', sa.Uuid(), nullable=True),
    sa.Column('role', sa.String(length=20), nullable=False),
    sa.Column('state', sa.String(length=20), nullable=False),
    sa.Column('machine', sa.String(length=200), nullable=True),
    sa.Column('workdir', sa.String(length=1000), nullable=True),
    sa.Column('client', sa.String(length=200), nullable=True),
    sa.Column('last_checkpoint_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('ended_by', sa.Uuid(), nullable=True),
    sa.Column('end_reason', sa.Text(), nullable=True),
    sa.Column('result', sa.Text(), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['ended_by'], ['users.id'], ),
    sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['work_package_id'], ['work_packages.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_task_sessions_task_id'), 'task_sessions', ['task_id'], unique=False)
    op.create_index('uq_task_sessions_active_executor', 'task_sessions', ['task_id'], unique=True,
                    postgresql_where=sa.text("state = 'active' AND role = 'executor'"))
    op.create_table('session_checkpoints',
    sa.Column('session_id', sa.Uuid(), nullable=False),
    sa.Column('note', sa.Text(), nullable=False),
    sa.Column('data', postgresql.JSONB(astext_type=Text()), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['session_id'], ['task_sessions.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_session_checkpoints_session_id'), 'session_checkpoints', ['session_id'], unique=False)
    op.add_column('result_proposals', sa.Column('session_id', sa.Uuid(), nullable=True))
    op.create_foreign_key('result_proposals_session_id_fkey', 'result_proposals', 'task_sessions',
                          ['session_id'], ['id'])
    op.add_column('audit_events', sa.Column('session_id', sa.Uuid(), nullable=True))


def downgrade() -> None:
    op.drop_column('audit_events', 'session_id')
    op.drop_constraint('result_proposals_session_id_fkey', 'result_proposals', type_='foreignkey')
    op.drop_column('result_proposals', 'session_id')
    op.drop_index(op.f('ix_session_checkpoints_session_id'), table_name='session_checkpoints')
    op.drop_table('session_checkpoints')
    op.drop_index('uq_task_sessions_active_executor', table_name='task_sessions')
    op.drop_index(op.f('ix_task_sessions_task_id'), table_name='task_sessions')
    op.drop_table('task_sessions')
