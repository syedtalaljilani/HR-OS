"""add company_location to org settings

Revision ID: 9c2e4f6a8d10
Revises: 7a0d3e5b9c1f
Create Date: 2026-09-09 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9c2e4f6a8d10"
down_revision: Union[str, Sequence[str], None] = "7a0d3e5b9c1f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "org_settings",
        sa.Column("company_location", sa.Text(), nullable=False, server_default=""),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("org_settings", "company_location")