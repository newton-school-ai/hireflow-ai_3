"""initial_schema

Revision ID: 001
Revises: 
Create Date: 2026-06-25 02:12:46.435884

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('jobs',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('company_name', sa.String(), nullable=False),
    sa.Column('role_title', sa.String(), nullable=False),
    sa.Column('jd_text', sa.Text(), nullable=False),
    sa.Column('location', sa.String(), nullable=True),
    sa.Column('application_url', sa.String(), nullable=True),
    sa.Column('posting_date', sa.String(), nullable=True),
    sa.Column('listing_type', sa.String(), nullable=True),
    sa.Column('is_spam', sa.Boolean(), nullable=False),
    sa.Column('spam_confidence', sa.Float(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('users',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('email', sa.String(), nullable=False),
    sa.Column('mode', sa.String(), nullable=True),
    sa.Column('master_profile', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('weekly_quota', sa.Integer(), nullable=True),
    sa.Column('confirmation_mode', sa.String(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_table('applications',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('job_id', sa.Integer(), nullable=False),
    sa.Column('match_score', sa.Float(), nullable=True),
    sa.Column('skill_gaps', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('resume_path', sa.String(), nullable=True),
    sa.Column('status', sa.String(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('prep_guides',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('job_id', sa.Integer(), nullable=False),
    sa.Column('company_intel', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('rounds', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('topics', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('mock_questions', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('weekly_reports',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('week_start', sa.Date(), nullable=True),
    sa.Column('applied_count', sa.Integer(), nullable=False),
    sa.Column('avg_match_score', sa.Float(), nullable=True),
    sa.Column('report_path', sa.String(), nullable=True),
    sa.Column('email_sent_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('weekly_reports')
    op.drop_table('prep_guides')
    op.drop_table('applications')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
    op.drop_table('jobs')
