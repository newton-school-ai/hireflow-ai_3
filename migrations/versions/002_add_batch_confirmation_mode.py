"""add_batch_confirmation_mode

Revision ID: 15e7936f4058
Revises: 001
Create Date: 2026-07-05 09:45:31.838120

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, Sequence[str], None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Since Postgres enums cannot be easily updated within transactions in some versions,
    # we use autocommit block to add the value to the enum type.
    op.execute("COMMIT")  # End current transaction
    op.execute("ALTER TYPE confirmationmode ADD VALUE 'batch'")
    # We don't need alter_column if it's Python-side default, but setting it as default is safe.


def downgrade() -> None:
    """Downgrade schema."""
    # Dropping a value from an enum type is not directly supported by PostgreSQL
    # without recreating the enum, so we leave this as a no-op.
    pass
