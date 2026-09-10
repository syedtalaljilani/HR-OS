import uuid

from pydantic import BaseModel


class InvitePublicOut(BaseModel):
    """Info shown on the public invite landing page before applying."""

    job_id: uuid.UUID
    job_title: str
    job_location: str | None = None
    candidate_name: str | None = None
    candidate_email: str | None = None
    company_name: str = ""


class InviteApplyResponse(BaseModel):
    applicationId: str
    status: str
    customerId: str
    trackingUrl: str