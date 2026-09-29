"""initial_schema

Explicit snapshot of the schema as of 2026-05-16 (models at commit 1bb2489).
Until 2026-09-29 this revision ran Base.metadata.create_all from the *current*
models, which made later revisions collide with columns it had already created.
Databases already stamped with this revision are unaffected by the rewrite.

Revision ID: 993840ac9a18
Revises:
Create Date: 2026-05-16 18:51:46.080897

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import String, Text
from sqlalchemy.dialects import postgresql

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
    op.create_table('link_types',
    sa.Column('name', sa.String(length=50), nullable=False),
    sa.Column('outward_name', sa.String(length=100), nullable=False),
    sa.Column('inward_name', sa.String(length=100), nullable=False),
    sa.Column('is_directed', sa.Boolean(), nullable=False),
    sa.Column('color', sa.String(length=30), nullable=True),
    sa.Column('constraint', postgresql.JSONB(astext_type=Text()), nullable=True),
    sa.Column('position', sa.Integer(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name')
    )
    op.create_table('users',
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('display_name', sa.String(length=255), nullable=False),
    sa.Column('keycloak_id', sa.String(length=255), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('is_superuser', sa.Boolean(), nullable=False),
    sa.Column('timezone', sa.String(length=50), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('email'),
    sa.UniqueConstraint('keycloak_id')
    )
    op.create_table('gantt_charts',
    sa.Column('owner_id', sa.Uuid(), nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('settings', postgresql.JSONB(astext_type=Text()), nullable=False),
    sa.Column('position', sa.Integer(), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('projects',
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('key', sa.String(length=10), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('visibility', sa.Enum('public', 'restricted', name='projectvisibility', native_enum=False, length=20), nullable=False),
    sa.Column('owner_id', sa.Uuid(), nullable=False),
    sa.Column('is_archived', sa.Boolean(), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('key')
    )
    op.create_table('project_members',
    sa.Column('project_id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('role', sa.Enum('admin', 'manager', 'member', 'viewer', name='projectmemberrole', native_enum=False, length=20), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('project_id', 'user_id')
    )
    op.create_table('views',
    sa.Column('project_id', sa.Uuid(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('type', sa.Enum('kanban', 'backlog', 'epic_tree', name='viewtype', native_enum=False, length=20), nullable=False),
    sa.Column('position', sa.Integer(), nullable=False),
    sa.Column('is_default', sa.Boolean(), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_views_project_position', 'views', ['project_id', 'position'], unique=False)
    op.create_table('workflows',
    sa.Column('project_id', sa.Uuid(), nullable=True),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('is_default', sa.Boolean(), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('board_columns',
    sa.Column('view_id', sa.Uuid(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('position', sa.Integer(), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['view_id'], ['views.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_board_columns_view_position', 'board_columns', ['view_id', 'position'], unique=False)
    op.create_table('statuses',
    sa.Column('workflow_id', sa.Uuid(), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('category', sa.Enum('initial', 'intermediate', 'final', name='statuscategory', native_enum=False, length=20), nullable=False),
    sa.Column('is_default', sa.Boolean(), nullable=False),
    sa.Column('position', sa.Integer(), nullable=False),
    sa.Column('color', sa.String(length=7), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['workflow_id'], ['workflows.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('task_types',
    sa.Column('project_id', sa.Uuid(), nullable=True),
    sa.Column('key', sa.String(length=50), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('is_system', sa.Boolean(), nullable=False),
    sa.Column('color', sa.String(length=20), nullable=True),
    sa.Column('icon', sa.String(length=50), nullable=True),
    sa.Column('meta_schema', postgresql.JSONB(astext_type=Text()), nullable=True),
    sa.Column('default_workflow_id', sa.Uuid(), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['default_workflow_id'], ['workflows.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('board_column_statuses',
    sa.Column('board_column_id', sa.Uuid(), nullable=False),
    sa.Column('status_id', sa.Uuid(), nullable=False),
    sa.ForeignKeyConstraint(['board_column_id'], ['board_columns.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['status_id'], ['statuses.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('board_column_id', 'status_id')
    )
    op.create_table('project_task_type_configs',
    sa.Column('project_id', sa.Uuid(), nullable=False),
    sa.Column('task_type_id', sa.Uuid(), nullable=False),
    sa.Column('workflow_id', sa.Uuid(), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['task_type_id'], ['task_types.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['workflow_id'], ['workflows.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('project_id', 'task_type_id')
    )
    op.create_table('tasks',
    sa.Column('project_id', sa.Uuid(), nullable=False),
    sa.Column('workflow_id', sa.Uuid(), nullable=False),
    sa.Column('task_type_id', sa.Uuid(), nullable=False),
    sa.Column('reporter_id', sa.Uuid(), nullable=False),
    sa.Column('assignee_id', sa.Uuid(), nullable=True),
    sa.Column('parent_task_id', sa.Uuid(), nullable=True),
    sa.Column('current_status_id', sa.Uuid(), nullable=False),
    sa.Column('key', sa.String(length=30), nullable=False),
    sa.Column('title', sa.String(length=500), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('priority', sa.Enum('low', 'medium', 'high', 'critical', name='taskpriority', native_enum=False, length=20), nullable=False),
    sa.Column('meta', postgresql.JSONB(astext_type=Text()), nullable=False),
    sa.Column('start_date', sa.Date(), nullable=True),
    sa.Column('due_date', sa.Date(), nullable=True),
    sa.Column('duration_days', sa.Integer(), nullable=True),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.Column('search_vector', postgresql.TSVECTOR(), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['assignee_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['current_status_id'], ['statuses.id'], ),
    sa.ForeignKeyConstraint(['parent_task_id'], ['tasks.id'], ),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['reporter_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['task_type_id'], ['task_types.id'], ),
    sa.ForeignKeyConstraint(['workflow_id'], ['workflows.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('key')
    )
    op.create_table('transitions',
    sa.Column('workflow_id', sa.Uuid(), nullable=False),
    sa.Column('from_status_id', sa.Uuid(), nullable=False),
    sa.Column('to_status_id', sa.Uuid(), nullable=False),
    sa.Column('required_role', sa.String(length=50), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['from_status_id'], ['statuses.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['to_status_id'], ['statuses.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['workflow_id'], ['workflows.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('comments',
    sa.Column('task_id', sa.Uuid(), nullable=False),
    sa.Column('author_id', sa.Uuid(), nullable=False),
    sa.Column('parent_comment_id', sa.Uuid(), nullable=True),
    sa.Column('content', sa.Text(), nullable=False),
    sa.Column('labels', postgresql.ARRAY(String(length=50)), nullable=False),
    sa.Column('edited_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['author_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['parent_comment_id'], ['comments.id'], ),
    sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('gantt_chart_tasks',
    sa.Column('gantt_id', sa.Uuid(), nullable=False),
    sa.Column('task_id', sa.Uuid(), nullable=False),
    sa.Column('position', sa.Integer(), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['gantt_id'], ['gantt_charts.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('notifications',
    sa.Column('recipient_id', sa.Uuid(), nullable=False),
    sa.Column('event_type', sa.Enum('task_assigned', 'awaiting_decision', 'revision_requested', 'decision_made', 'task_closed', 'decision_reminder', name='notificationeventtype', native_enum=False, length=40), nullable=False),
    sa.Column('entity_type', sa.Enum('task', 'solution', name='notificationentitytype', native_enum=False, length=20), nullable=False),
    sa.Column('entity_id', sa.Uuid(), nullable=False),
    sa.Column('task_id', sa.Uuid(), nullable=True),
    sa.Column('message', sa.Text(), nullable=False),
    sa.Column('is_read', sa.Boolean(), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['recipient_id'], ['users.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_notifications_recipient_unread', 'notifications', ['recipient_id', 'is_read', 'created_at'], unique=False)
    op.create_table('task_links',
    sa.Column('source_task_id', sa.Uuid(), nullable=False),
    sa.Column('target_task_id', sa.Uuid(), nullable=False),
    sa.Column('link_type_id', sa.Uuid(), nullable=False),
    sa.Column('created_by', sa.Uuid(), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
    sa.ForeignKeyConstraint(['link_type_id'], ['link_types.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['source_task_id'], ['tasks.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['target_task_id'], ['tasks.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )

    for stmt in _FTS_UPGRADE:
        op.execute(sa.text(stmt))


def downgrade() -> None:
    for stmt in _FTS_DOWNGRADE:
        op.execute(sa.text(stmt))

    op.drop_table('task_links')
    op.drop_index('ix_notifications_recipient_unread', table_name='notifications')
    op.drop_table('notifications')
    op.drop_table('gantt_chart_tasks')
    op.drop_table('comments')
    op.drop_table('transitions')
    op.drop_table('tasks')
    op.drop_table('project_task_type_configs')
    op.drop_table('board_column_statuses')
    op.drop_table('task_types')
    op.drop_table('statuses')
    op.drop_index('ix_board_columns_view_position', table_name='board_columns')
    op.drop_table('board_columns')
    op.drop_table('workflows')
    op.drop_index('ix_views_project_position', table_name='views')
    op.drop_table('views')
    op.drop_table('project_members')
    op.drop_table('projects')
    op.drop_table('gantt_charts')
    op.drop_table('users')
    op.drop_table('link_types')
