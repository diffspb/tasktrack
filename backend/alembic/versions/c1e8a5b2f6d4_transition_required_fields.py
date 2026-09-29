"""transition required fields (FR-003, TT-13, ADR-023)

Revision ID: c1e8a5b2f6d4
Revises: b9d7f4a1e5c3
Create Date: 2026-09-30 16:00:00

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import Text
from sqlalchemy.dialects import postgresql

revision: str = 'c1e8a5b2f6d4'
down_revision: Union[str, Sequence[str], None] = 'b9d7f4a1e5c3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('transitions', sa.Column(
        'required_fields', postgresql.JSONB(astext_type=Text()), server_default='[]', nullable=False,
    ))


def downgrade() -> None:
    op.drop_column('transitions', 'required_fields')
