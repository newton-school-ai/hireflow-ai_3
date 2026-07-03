"""add batch confirmation mode

Revision ID: 002
Revises: 001
Create Date: 2026-07-03 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, Sequence[str], None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add 'batch' to the confirmationmode enum and update the default."""
    # Add 'batch' value to the existing PostgreSQL enum type
    op.execute("ALTER TYPE confirmationmode ADD VALUE IF NOT EXISTS 'batch'")
    # Update default to 'batch'
    op.execute("ALTER TABLE users ALTER COLUMN confirmation_mode SET DEFAULT 'batch'")


def downgrade() -> None:
    """Revert to the original default. Note: PostgreSQL does not support removing enum values."""
    op.execute("ALTER TABLE users ALTER COLUMN confirmation_mode SET DEFAULT 'manual'")
