"""result proposals and reviews (FR-003, TT-14–17, ADR-021)

Migrates the Decision Process surrogate: every live comment labelled `solution`
becomes a ResultProposal with status `historical` ("историческое, формально не
проверено"), Task.meta.solution_comment_id is dropped.

Revision ID: a8c6e3f0d4b2
Revises: f7b5d2e9c3a1
Create Date: 2026-09-30 12:00:00

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import Text
from sqlalchemy.dialects import postgresql

revision: str = 'a8c6e3f0d4b2'
down_revision: Union[str, Sequence[str], None] = 'f7b5d2e9c3a1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('project_members', sa.Column('is_reviewer', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('task_types', sa.Column('requires_review', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('tasks', sa.Column('reviewer_id', sa.Uuid(), nullable=True))
    op.add_column('tasks', sa.Column('result_state', sa.String(length=30), server_default='none', nullable=False))
    op.add_column('tasks', sa.Column('delivery', postgresql.JSONB(astext_type=Text()), nullable=True))
    op.add_column('tasks', sa.Column('recipient_acceptance', postgresql.JSONB(astext_type=Text()), nullable=True))
    op.create_foreign_key('tasks_reviewer_id_fkey', 'tasks', 'users', ['reviewer_id'], ['id'])

    op.create_table('result_proposals',
    sa.Column('task_id', sa.Uuid(), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.Column('author_id', sa.Uuid(), nullable=False),
    sa.Column('work_package_id', sa.Uuid(), nullable=True),
    sa.Column('supersedes_id', sa.Uuid(), nullable=True),
    sa.Column('status', sa.Enum('submitted', 'accepted', 'changes_requested', 'rejected', 'withdrawn', 'superseded', 'historical', name='proposalstatus', native_enum=False, length=30), nullable=False),
    sa.Column('summary', sa.Text(), nullable=False),
    sa.Column('links', postgresql.JSONB(astext_type=Text()), nullable=False),
    sa.Column('criteria', postgresql.JSONB(astext_type=Text()), nullable=False),
    sa.Column('checks', postgresql.JSONB(astext_type=Text()), nullable=False),
    sa.Column('limitations', sa.Text(), nullable=True),
    sa.Column('provenance', postgresql.JSONB(astext_type=Text()), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['author_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['supersedes_id'], ['result_proposals.id'], ),
    sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['work_package_id'], ['work_packages.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('task_id', 'version')
    )
    op.create_index(op.f('ix_result_proposals_task_id'), 'result_proposals', ['task_id'], unique=False)
    op.create_table('reviews',
    sa.Column('proposal_id', sa.Uuid(), nullable=False),
    sa.Column('reviewer_id', sa.Uuid(), nullable=False),
    sa.Column('verdict', sa.Enum('accepted', 'changes_requested', 'rejected', name='reviewverdict', native_enum=False, length=30), nullable=False),
    sa.Column('criteria', postgresql.JSONB(astext_type=Text()), nullable=False),
    sa.Column('rationale', sa.Text(), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['proposal_id'], ['result_proposals.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['reviewer_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_reviews_proposal_id'), 'reviews', ['proposal_id'], unique=False)

    # Surrogate → historical proposals (never formally reviewed).
    op.execute(sa.text("""
        INSERT INTO result_proposals
            (id, task_id, version, author_id, status, summary, links, criteria, checks,
             provenance, created_at, updated_at)
        SELECT gen_random_uuid(), c.task_id,
               row_number() OVER (PARTITION BY c.task_id ORDER BY c.created_at),
               c.author_id, 'historical', c.content, '[]', '[]', '[]',
               jsonb_build_object('migrated_from_comment', c.id::text,
                                  'note', 'историческое, формально не проверено'),
               c.created_at, c.created_at
        FROM comments c
        WHERE 'solution' = ANY(c.labels) AND c.deleted_at IS NULL
    """))
    op.execute(sa.text("""
        UPDATE tasks SET result_state = 'historical'
        WHERE id IN (SELECT task_id FROM result_proposals WHERE status = 'historical')
    """))
    op.execute(sa.text("UPDATE tasks SET meta = meta - 'solution_comment_id' WHERE meta ? 'solution_comment_id'"))


def downgrade() -> None:
    op.drop_index(op.f('ix_reviews_proposal_id'), table_name='reviews')
    op.drop_table('reviews')
    op.drop_index(op.f('ix_result_proposals_task_id'), table_name='result_proposals')
    op.drop_table('result_proposals')
    op.drop_constraint('tasks_reviewer_id_fkey', 'tasks', type_='foreignkey')
    op.drop_column('tasks', 'recipient_acceptance')
    op.drop_column('tasks', 'delivery')
    op.drop_column('tasks', 'result_state')
    op.drop_column('tasks', 'reviewer_id')
    op.drop_column('task_types', 'requires_review')
    op.drop_column('project_members', 'is_reviewer')
