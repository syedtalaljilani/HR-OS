"""add interview reminder_sent_at

Revision ID: a7b8c9d0e1f2
Revises: d4e5f6a7b8c9
Create Date: 2026-09-10 00:00:00
"""
from datetime import datetime, timezone

import sqlalchemy as sa
from alembic import op

revision = "a7b8c9d0e1f2"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "interviews",
        sa.Column(
            "reminder_sent_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("interviews", "reminder_sent_at")