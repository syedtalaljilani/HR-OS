"""add source and action to screening queue

Revision ID: a2b3c4d5e6f7
Revises: a1b2c3d4e5f6
Create Date: 2026-09-10 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a2b3c4d5e6f7"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "screening_queue",
        sa.Column("source", sa.String(length=32), nullable=False, server_default="AUTO"),
    )
    op.add_column(
        "screening_queue",
        sa.Column("action", sa.String(length=32), nullable=False, server_default="EVALUATE"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("screening_queue", "action")
    op.drop_column("screening_queue", "source")