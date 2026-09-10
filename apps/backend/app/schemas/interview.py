import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.db.models.enums import InterviewStatus, InterviewType


class InterviewCreate(BaseModel):
    type: InterviewType = InterviewType.HR
    scheduled_at: datetime
    location: str | None = None
    notes: str | None = None


class InterviewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    application_id: uuid.UUID
    type: InterviewType
    scheduled_at: datetime
    status: InterviewStatus
    location: str | None = None
    notes: str | None = None
    created_at: datetime