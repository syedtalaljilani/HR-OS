import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class CandidateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    email: EmailStr
    phone: str | None
    address: str | None
    profile_data: dict | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None


class CandidateUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=500)
    email: EmailStr | None = None
    phone: str | None = None
    address: str | None = None
    profile_data: dict | None = None