import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import settings
from app.db.database import Base
from app.db.models.enums import (
    AssignmentStatus,
    InterviewRequestStatus,
    InterviewRequestType,
    InterviewStatus,
    InterviewType,
)


class Interview(Base):
    __tablename__ = "interviews"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type: Mapped[InterviewType] = mapped_column(
        Enum(InterviewType, name="interview_type"), nullable=False
    )
    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    status: Mapped[InterviewStatus] = mapped_column(
        Enum(InterviewStatus, name="interview_status"),
        nullable=False,
        default=InterviewStatus.SCHEDULED,
    )
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    available_slots: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    reschedule_token: Mapped[str | None] = mapped_column(String(128), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reminder_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    application: Mapped["Application"] = relationship(back_populates="interviews")
    assignments: Mapped[list["InterviewAssignment"]] = relationship(
        back_populates="interview", cascade="all, delete-orphan"
    )
    scorecards: Mapped[list["InterviewScorecard"]] = relationship(
        back_populates="interview", cascade="all, delete-orphan"
    )
    combined_score: Mapped["InterviewCombinedScore"] = relationship(
        back_populates="interview", cascade="all, delete-orphan", uselist=False
    )
    requests: Mapped[list["InterviewRequest"]] = relationship(
        back_populates="interview", cascade="all, delete-orphan"
    )

    @property
    def reschedule_link(self) -> str | None:
        if self.reschedule_token:
            return f"{settings.PUBLIC_BASE_URL.rstrip('/')}/reschedule/{self.reschedule_token}"
        return None


class InterviewRequest(Base):
    __tablename__ = "interview_requests"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    interview_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("interviews.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    type: Mapped[InterviewRequestType] = mapped_column(
        Enum(InterviewRequestType, name="interview_request_type"),
        nullable=False,
        default=InterviewRequestType.REMOTE,
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    proposed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    awaiting_time: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    status: Mapped[InterviewRequestStatus] = mapped_column(
        Enum(InterviewRequestStatus, name="interview_request_status"),
        nullable=False,
        default=InterviewRequestStatus.PENDING,
    )
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    application: Mapped["Application"] = relationship(
        back_populates="interview_requests"
    )
    interview: Mapped["Interview"] = relationship(back_populates="requests")


class InterviewAssignment(Base):
    __tablename__ = "interview_assignments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    interview_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("interviews.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    interviewer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    assigned_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[AssignmentStatus] = mapped_column(
        Enum(AssignmentStatus, name="assignment_status"),
        nullable=False,
        default=AssignmentStatus.ASSIGNED,
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    interview: Mapped["Interview"] = relationship(back_populates="assignments")


class InterviewScorecard(Base):
    __tablename__ = "interview_scorecards"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    interview_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("interviews.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    interviewer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    scores: Mapped[dict] = mapped_column(JSONB, nullable=True)
    total_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=True)
    comments: Mapped[str] = mapped_column(Text, nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    interview: Mapped["Interview"] = relationship(back_populates="scorecards")


class InterviewCombinedScore(Base):
    __tablename__ = "interview_combined_scores"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    interview_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("interviews.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    combined_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    interviewer_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    interview: Mapped["Interview"] = relationship(back_populates="combined_score")