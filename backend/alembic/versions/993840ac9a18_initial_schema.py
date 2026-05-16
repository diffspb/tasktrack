"""initial_schema

Revision ID: 993840ac9a18
Revises:
Create Date: 2026-05-16 18:51:46.080897

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = '993840ac9a18'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# FTS machinery for tasks.search_vector — kept in sync by a Postgres trigger.
_FTS_UPGRADE = [
    """
    CREATE OR REPLACE FUNCTION tasks_search_vector_update() RETURNS trigger AS $$
    BEGIN
      NEW.search_vector :=
        to_tsvector('russian',
          coalesce(NEW.title, '') || ' ' || coalesce(NEW.description, ''));
      RETURN NEW;
    END
    $$ LANGUAGE plpgsql
    """,
    "DROP TRIGGER IF EXISTS tasks_search_vector_trigger ON tasks",
    """
    CREATE TRIGGER tasks_search_vector_trigger
    BEFORE INSERT OR UPDATE OF title, description ON tasks
    FOR EACH ROW EXECUTE FUNCTION tasks_search_vector_update()
    """,
    "CREATE INDEX IF NOT EXISTS ix_tasks_search_vector ON tasks USING GIN (search_vector)",
]

_FTS_DOWNGRADE = [
    "DROP INDEX IF EXISTS ix_tasks_search_vector",
    "DROP TRIGGER IF EXISTS tasks_search_vector_trigger ON tasks",
    "DROP FUNCTION IF EXISTS tasks_search_vector_update",
]


def upgrade() -> None:
    # Create all tables from SQLAlchemy metadata (equivalent to create_all).
    # Using checkfirst=True (default) makes this idempotent on existing DBs.
    conn = op.get_bind()
    from app.models.base import Base
    import app.models  # noqa: F401 — registers all models on Base.metadata
    Base.metadata.create_all(bind=conn)

    for stmt in _FTS_UPGRADE:
        conn.execute(sa.text(stmt))


def downgrade() -> None:
    for stmt in _FTS_DOWNGRADE:
        op.execute(sa.text(stmt))

    conn = op.get_bind()
    from app.models.base import Base
    import app.models  # noqa: F401
    Base.metadata.drop_all(bind=conn)
