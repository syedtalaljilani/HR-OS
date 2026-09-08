"""add file hash to cv documents

Revision ID: d47a3b16ee74
Revises: c8518739d13e
Create Date: 2026-09-08 17:24:43.970806

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd47a3b16ee74'
down_revision: Union[str, Sequence[str], None] = 'c8518739d13e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "cv_documents",
        sa.Column("file_hash", sa.String(length=64), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("cv_documents", "file_hash")
