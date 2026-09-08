import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.db.models.enums import JobStatus


class JobCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    requirements: dict | None = None
    location: str | None = None
    salary_min: Decimal | None = Field(default=None, ge=0)
    salary_max: Decimal | None = Field(default=None, ge=0)
    status: JobStatus = JobStatus.DRAFT


class JobUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    requirements: dict | None = None
    location: str | None = None
    salary_min: Decimal | None = Field(default=None, ge=0)
    salary_max: Decimal | None = Field(default=None, ge=0)
    status: JobStatus | None = None


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    description: str | None
    requirements: dict | None
    location: str | None
    salary_min: Decimal | None
    salary_max: Decimal | None
    status: JobStatus
    created_by: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


class JobPublishOut(JobOut):
    pass


class JobAssistantRequest(BaseModel):
    user_input: str = Field(min_length=1, max_length=4000)
    job_title: str | None = Field(default=None, max_length=255)


class JobAssistantOut(BaseModel):
    description: str
    model: str | None = None