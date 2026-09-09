import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.db.models.enums import ApplicationStatus, ExtractionStatus, HRDecision


class ApplicationCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=500)
    email: EmailStr
    phone: str | None = None
    address: str | None = None
    expected_salary: Decimal | None = Field(default=None, ge=0)
    consent: bool = False
    skills: str | None = None
    education: str | None = None
    experience: str | None = None
    profile_data: str | None = None


class ApplicationTrackingResponse(BaseModel):
    application_id: str
    status: ApplicationStatus
    candidate_name: str
    job_title: str
    created_at: datetime
    updated_at: datetime
    status_history: list["ApplicationHistoryOut"] = []


class ApplicationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    application_id: str
    candidate_id: uuid.UUID
    job_id: uuid.UUID
    expected_salary: Decimal | None
    status: ApplicationStatus
    consent: bool
    created_at: datetime
    updated_at: datetime


class ApplicationDetail(ApplicationOut):
    candidate_name: str | None = None
    candidate_email: str | None = None
    candidate_phone: str | None = None
    job_title: str | None = None
    cv_documents: list["CVDocumentOut"] = []
    screening: "ScreeningOut | None" = None
    status_history: list["ApplicationHistoryOut"] = []


class CVDocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    file_name: str
    mime_type: str | None
    extraction_status: ExtractionStatus
    created_at: datetime


class ScreeningOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    application_id: uuid.UUID
    recommendation: str | None
    score: Decimal | None
    evidence: dict | None
    missing_requirements: dict | None
    uncertainty: dict | None
    model: str | None
    hr_decision: HRDecision
    reviewed_by: uuid.UUID | None
    created_at: datetime


class ApplicationHistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    application_id: uuid.UUID
    from_status: str | None
    to_status: str
    changed_by: uuid.UUID | None
    reason: str | None
    created_at: datetime


class ScreeningRequest(BaseModel):
    pass


class OverrideRequest(BaseModel):
    recommendation: str
    score: float | None = None
    note: str | None = None
    hr_decision: HRDecision = HRDecision.OVERRIDDEN


class StatusUpdate(BaseModel):
    status: ApplicationStatus
    reason: str | None = None


class DecisionRequest(BaseModel):
    decision: ApplicationStatus
    reason: str | None = None


ApplicationTrackingResponse.model_rebuild()
ApplicationDetail.model_rebuild()