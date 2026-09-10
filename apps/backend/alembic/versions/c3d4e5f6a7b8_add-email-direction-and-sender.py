"""add direction and sender_email to emails

Revision ID: c3d4e5f6a7b8
Revises: b1c2d3e4f5a6
Create Date: 2026-09-10 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, None] = "b1c2d3e4f5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    direction = sa.Enum(
        "INBOUND", "OUTBOUND", name="email_direction"
    )
    direction.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "emails",
        sa.Column(
            "direction",
            sa.Enum("INBOUND", "OUTBOUND", name="email_direction"),
            server_default=sa.text("'OUTBOUND'"),
            nullable=False,
        ),
    )
    op.add_column(
        "emails",
        sa.Column("sender_email", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("emails", "sender_email")
    op.drop_column("emails", "direction")
    sa.Enum(name="email_direction").drop(op.get_bind(), checkfirst=True)