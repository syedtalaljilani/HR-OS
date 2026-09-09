import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, require_hr_or_admin
from app.db.models import Application, User
from app.db.models.email import Email
from app.db.models.enums import EmailType
from app.services import email_agent_service, email_service

router = APIRouter(
    prefix="/applications/{application_id}/email", tags=["Emails"]
)


class EmailSendRequest(BaseModel):
    type: EmailType
    subject: str | None = None
    body: str | None = None


class EmailAssistantRequest(BaseModel):
    email_type: EmailType | None = None
    reason: str | None = None
    context: dict | None = None
    hr_notes: str | None = None
    tone: str | None = None


class EmailAssistantOut(BaseModel):
    subject: str
    body: str
    model: str | None = None


class EmailOut(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    application_id: uuid.UUID | None
    type: EmailType
    recipient: str
    subject: str
    body: str | None = None
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


@router.post("/assistant", response_model=EmailAssistantOut)
def email_assistant_draft(
    application_id: uuid.UUID,
    data: EmailAssistantRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_hr_or_admin),
):
    """AI email-writing assistant for HR.

    Drafts a subject + body for the candidate using the application context
    (candidate name, job title, latest screening reason/score) combined with
    free-form HR notes. The draft is returned for HR review — nothing is sent.
    """
    application = _get_application(db, application_id)

    context = dict(data.context or {})
    screening = application.screening_results[-1] if application.screening_results else None
    if screening is not None and screening.score is not None:
        context.setdefault("score", float(screening.score))
    if screening is not None and isinstance(screening.evidence, dict):
        items = screening.evidence.get("items") or []
        missing = [
            it.get("requirement")
            for it in items
            if isinstance(it, dict) and it.get("status") == "MISSING" and it.get("requirement")
        ]
        if missing:
            context.setdefault("missing", missing[:6])

    return email_agent_service.draft_email(
        email_type=data.email_type.value if data.email_type else None,
        candidate_name=application.candidate.full_name if application.candidate else None,
        job_title=application.job.title if application.job else None,
        reason=data.reason,
        context=context,
        hr_notes=data.hr_notes,
        tone=data.tone,
        db=db,
    )


@router.post("/flush", response_model=dict)
def flush_pending(
    db: Session = Depends(get_db),
    _: User = Depends(require_hr_or_admin),
):
    """Re-attempt delivery for all emails stuck in PENDING or FAILED."""
    return email_service.flush_pending_emails(db)