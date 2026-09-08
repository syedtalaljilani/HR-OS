import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, require_hr_or_admin
from app.db.models import Application, User
from app.db.models.email import Email
from app.db.models.enums import EmailType
from app.services import email_service

router = APIRouter(
    prefix="/applications/{application_id}/email", tags=["Emails"]
)


class EmailSendRequest(BaseModel):
    type: EmailType
    subject: str | None = None
    body: str | None = None


class EmailOut(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    application_id: uuid.UUID | None
    type: EmailType
    recipient: str
    subject: str
    status: str
    sent_at: object | None
    created_at: object | None


def _get_application(db: Session, application_id: uuid.UUID) -> Application:
    application = db.get(Application, application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found")
    return application


@router.post("", response_model=EmailOut)
def send_email(
    application_id: uuid.UUID,
    data: EmailSendRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_hr_or_admin),
):
    application = _get_application(db, application_id)
    subject = data.subject or email_service.application_email_subject(
        application, data.type
    )
    body = data.body or email_service.application_email_body(application, data.type)
    recipient = application.candidate.email if application.candidate else None
    if not recipient:
        raise HTTPException(status_code=400, detail="Candidate email not available")

    email = email_service.record_email(
        db,
        application_id=application.id,
        email_type=data.type,
        recipient=recipient,
        subject=subject,
        body=body,
        send=True,
    )
    return EmailOut.model_validate(email)


@router.get("", response_model=list[EmailOut])
def email_history(
    application_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_hr_or_admin),
):
    application = _get_application(db, application_id)
    rows = (
        db.query(Email)
        .filter(Email.application_id == application.id)
        .order_by(Email.created_at.desc())
        .all()
    )
    return [EmailOut.model_validate(e) for e in rows]