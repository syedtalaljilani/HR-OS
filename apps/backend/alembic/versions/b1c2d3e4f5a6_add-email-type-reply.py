"""add REPLY to the email_type enum

Revision ID: b1c2d3e4f5a6
Revises: a4e999b17d1c
Create Date: 2026-09-10 12:30:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "b1c2d3e4f5a6"
down_revision: Union[str, None] = "a4e999b17d1c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TYPE email_type ADD VALUE IF NOT EXISTS 'REPLY'"
    )


def downgrade() -> None:
    # PostgreSQL cannot drop an enum value that is in use; the extra value is
    # harmless, so downgrade is intentionally a no-op.
    pass