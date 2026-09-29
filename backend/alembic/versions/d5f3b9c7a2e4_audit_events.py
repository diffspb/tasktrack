"""audit events — durable audit log / event journal (FR-003, TT-06, ADR-018)

Revision ID: d5f3b9c7a2e4
Revises: c4d2a8e6f1b3
Create Date: 2026-09-29 16:00:00

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import Text
from sqlalchemy.dialects import postgresql

revision: str = 'd5f3b9c7a2e4'
down_revision: Union[str, Sequence[str], None] = 'c4d2a8e6f1b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('audit_events',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('xid', sa.BigInteger(), server_default=sa.text('(pg_current_xact_id()::text)::bigint'), nullable=False),
    sa.Column('occurred_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('actor_id', sa.Uuid(), nullable=True),
    sa.Column('project_id', sa.Uuid(), nullable=True),
    sa.Column('task_id', sa.Uuid(), nullable=True),
    sa.Column('entity_type', sa.String(length=30), nullable=False),
    sa.Column('entity_id', sa.Uuid(), nullable=False),
    sa.Column('action', sa.String(length=30), nullable=False),
    sa.Column('reason', sa.Text(), nullable=True),
    sa.Column('before', postgresql.JSONB(astext_type=Text()), nullable=True),
    sa.Column('after', postgresql.JSONB(astext_type=Text()), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_audit_events_project_cursor', 'audit_events', ['project_id', 'xid', 'id'], unique=False)
    op.create_index('ix_audit_events_task_cursor', 'audit_events', ['task_id', 'xid', 'id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_audit_events_task_cursor', table_name='audit_events')
    op.drop_index('ix_audit_events_project_cursor', table_name='audit_events')
    op.drop_table('audit_events')
