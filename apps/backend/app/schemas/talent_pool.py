import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.db.models.enums import TalentPoolStatus


class TalentPoolAdd(BaseModel):
    source_application_id: uuid.UUID | None = None
    consent: bool = False


class TalentPoolOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    candidate_id: uuid.UUID
    source_application_id: uuid.UUID | None
    status: TalentPoolStatus
    consent: bool
    added_by: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


class TalentPoolCandidateOut(TalentPoolOut):
    candidate_name: str | None = None
    candidate_email: str | None = None


class TalentPoolStatusUpdate(BaseModel):
    status: TalentPoolStatus


class TalentPoolMatchRequest(BaseModel):
    job_id: uuid.UUID
    limit: int = 20


class TalentPoolMatchItem(BaseModel):
    candidate_id: uuid.UUID
    candidate_name: str | None = None
    similarity: float = 0.0


class TalentPoolMatchResponse(BaseModel):
    matches: list[TalentPoolMatchItem] = []