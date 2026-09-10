"""add interview location and notes

Revision ID: 7a0d3e5b9c1f
Revises: 4b31c8d9f2a7
Create Date: 2026-09-09 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7a0d3e5b9c1f"
down_revision: Union[str, Sequence[str], None] = "4b31c8d9f2a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("interviews", sa.Column("location", sa.String(length=255), nullable=True))
    op.add_column("interviews", sa.Column("notes", sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("interviews", "notes")
    op.drop_column("interviews", "location")