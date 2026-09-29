"""idempotency keys — safe retry of commands (FR-003, TT-04, ADR-019)

Revision ID: e6a4c1d8b5f7
Revises: d5f3b9c7a2e4
Create Date: 2026-09-29 18:00:00

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import Text
from sqlalchemy.dialects import postgresql

revision: str = 'e6a4c1d8b5f7'
down_revision: Union[str, Sequence[str], None] = 'd5f3b9c7a2e4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('idempotency_keys',
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('key', sa.String(length=255), nullable=False),
    sa.Column('request_hash', sa.String(length=64), nullable=False),
    sa.Column('xid', sa.BigInteger(), server_default=sa.text('(pg_current_xact_id()::text)::bigint'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('status_code', sa.Integer(), nullable=True),
    sa.Column('response_body', sa.Text(), nullable=True),
    sa.Column('media_type', sa.String(length=100), nullable=True),
    sa.Column('project_ids', postgresql.JSONB(astext_type=Text()), nullable=True),
    sa.Column('system', sa.Boolean(), server_default='false', nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('user_id', 'key')
    )


def downgrade() -> None:
    op.drop_table('idempotency_keys')
