import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.db.models.enums import (
    InterviewRequestStatus,
    InterviewRequestType,
    InterviewStatus,
    InterviewType,
)


class InterviewCreate(BaseModel):
    type: InterviewType = InterviewType.HR
    scheduled_at: datetime
    location: str | None = None
    notes: str | None = None
    available_slots: list[datetime] | None = None


class InterviewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    application_id: uuid.UUID
    type: InterviewType
    scheduled_at: datetime
    status: InterviewStatus
    location: str | None = None
    available_slots: list[datetime] | None = None
    notes: str | None = None
    reschedule_link: str | None = None
    created_at: datetime


class InterviewRequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    application_id: uuid.UUID
    interview_id: uuid.UUID | None = None
    type: InterviewRequestType = InterviewRequestType.REMOTE
    reason: str | None = None
    proposed_at: datetime | None = None
    awaiting_time: bool = False
    status: InterviewRequestStatus
    created_at: datetime
    resolved_at: datetime | None = None


class RemoteReviewRequest(BaseModel):
    accept: bool
    meeting_link: str | None = None
    note: str | None = None


class SlotReviewRequest(BaseModel):
    accept: bool
    note: str | None = None


class RescheduleView(BaseModel):
    application_id: uuid.UUID
    candidate_name: str
    job_title: str
    interview_id: uuid.UUID
    type: InterviewType
    scheduled_at: datetime
    location: str | None = None
    notes: str | None = None
    available_slots: list[datetime] = []
    pending_remote: bool = False
    already_rescheduled: bool = False


class RescheduleSubmit(BaseModel):
    selected_slot: datetime | None = None
    remote_reason: str | None = None