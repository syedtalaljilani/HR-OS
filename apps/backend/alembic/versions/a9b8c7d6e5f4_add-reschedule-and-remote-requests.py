"""add interview available_slots, reschedule_token and interview_requests

Revision ID: a9b8c7d6e5f4
Revises: a7b8c9d0e1f2
Create Date: 2026-09-10 00:00:00
"""
from datetime import datetime, timezone

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "a9b8c7d6e5f4"
down_revision = "a7b8c9d0e1f2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "interviews",
        sa.Column(
            "available_slots",
            JSONB(),
            nullable=True,
        ),
    )
    op.add_column(
        "interviews",
        sa.Column(
            "reschedule_token",
            sa.String(length=128),
            nullable=True,
        ),
    )
    interview_request_type = sa.Enum(
        "REMOTE",
        name="interview_request_type",
        create_type=False,
    )
    interview_request_status = sa.Enum(
        "PENDING",
        "ACCEPTED",
        "DECLINED",
        name="interview_request_status",
        create_type=False,
    )
    op.create_table(
        "interview_requests",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "application_id",
            UUID(as_uuid=True),
            sa.ForeignKey("applications.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "interview_id",
            UUID(as_uuid=True),
            sa.ForeignKey("interviews.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "type",
            interview_request_type,
            nullable=False,
            server_default="REMOTE",
        ),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column(
            "status",
            interview_request_status,
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column(
            "resolved_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_interview_requests_application_id",
        "interview_requests",
        ["application_id"],
    )
    op.create_index(
        "ix_interview_requests_interview_id",
        "interview_requests",
        ["interview_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_interview_requests_interview_id", table_name="interview_requests")
    op.drop_index(
        "ix_interview_requests_application_id", table_name="interview_requests"
    )
    op.drop_table("interview_requests")
    op.drop_column("interviews", "reschedule_token")
    op.drop_column("interviews", "available_slots")
    op.execute("DROP TYPE IF EXISTS interview_request_type")
    op.execute("DROP TYPE IF EXISTS interview_request_status")