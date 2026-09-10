"""add candidate proposed interview-slot requests

Revision ID: e2f4a6b8c0d2
Revises: a9b8c7d6e5f4
Create Date: 2026-09-10 00:00:00
"""
import sqlalchemy as sa
from alembic import op

revision = "e2f4a6b8c0d2"
down_revision = "a9b8c7d6e5f4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE interview_request_type ADD VALUE 'NEW_SLOT'")
    op.add_column(
        "interview_requests",
        sa.Column("proposed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "interview_requests",
        sa.Column(
            "awaiting_time",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("interview_requests", "awaiting_time")
    op.drop_column("interview_requests", "proposed_at")
    # PostgreSQL cannot remove a value from an enum type; the value stays.