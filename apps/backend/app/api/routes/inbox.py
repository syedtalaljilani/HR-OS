import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, require_hr_or_admin
from app.db.models import Application, User
from app.db.models.email import Email
from app.db.models.enums import EmailDirection
from app.services import reply_agent_service

router = APIRouter(prefix="/emails", tags=["Email Agent"])


class InboxRequest(BaseModel):
    from_email: str
    subject: str | None = None
    text: str | None = None


class InboxOut(BaseModel):
    note: str
    candidate_name: str | None = None
    application_id: str | None = None
    interview_id: str | None = None
    interview_scheduled_at: str | None = None
    email_id: str | None = None
    subject: str | None = None
    body: str | None = None


class ProcessMissedOut(BaseModel):
    processed: list[dict] = []


class LastMessageOut(BaseModel):
    direction: str
    subject: str
    body: str | None = None
    created_at: datetime | None = None


class ConversationOut(BaseModel):
    application_id: str
    candidate_id: str | None = None
    candidate_name: str | None = None
    candidate_email: str | None = None
    job_title: str | None = None
    last_message: LastMessageOut | None = None
    unread: int = 0
    updated_at: datetime | None = None


@router.post("/inbox", response_model=InboxOut)
def receive_reply(
    data: InboxRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_hr_or_admin),
):
    """Ingest a candidate's reply to an outgoing email.

    The plug-in point for a mail-provider webhook / forwarding rule. Matches the
    sender with a candidate and auto-drafts + sends an interview follow-up.
    """
    return reply_agent_service.handle_reply(
        db, from_email=data.from_email, subject=data.subject, text=data.text
    )


@router.post("/process-missed", response_model=ProcessMissedOut)
def process_missed(
    db: Session = Depends(get_db),
    _: User = Depends(require_hr_or_admin),
):
    """Manually trigger the missed-interview check (also runs on a timer)."""
    return reply_agent_service.process_missed_interviews(db)


@router.post("/fetch", response_model=dict)
def fetch_mailbox(
    db: Session = Depends(get_db),
    _: User = Depends(require_hr_or_admin),
):
    """Pull unseen candidate replies from the configured mailbox now.

    Records each message in the dashboard chat and auto-replies when the sender
    is a known candidate. Also runs periodically when IMAP_ENABLED is on.
    """
    return reply_agent_service.fetch_mailbox(db)


@router.get("/conversations", response_model=list[ConversationOut])
def conversations(
    db: Session = Depends(get_db),
    _: User = Depends(require_hr_or_admin),
):
    """All candidate conversations (one per application), newest first.

    Each row carries the candidate identity, the last message for the list
    preview and the number of unread inbound messages for the badge.
    """
    apps = (
        db.query(Application)
        .filter(
            Application.deleted_at.is_(None),
            Application.candidate_id.isnot(None),
        )
        .order_by(Application.created_at.desc())
        .all()
    )
    rows: list[ConversationOut] = []
    for app in apps:
        emails = (
            db.query(Email)
            .filter(Email.application_id == app.id)
            .order_by(Email.created_at.desc(), Email.id.desc())
            .all()
        )
        if not emails:
            continue
        last = emails[0]
        unread = sum(
            1
            for e in emails
            if e.direction == EmailDirection.INBOUND and e.read_at is None
        )
        candidate = app.candidate
        rows.append(
            ConversationOut(
                application_id=str(app.id),
                candidate_id=str(candidate.id) if candidate else None,
                candidate_name=candidate.full_name if candidate else None,
                candidate_email=candidate.email if candidate else None,
                job_title=app.job.title if app.job else None,
                last_message=LastMessageOut(
                    direction=last.direction.value,
                    subject=last.subject,
                    body=last.body,
                    created_at=last.created_at,
                ),
                unread=unread,
                updated_at=last.created_at,
            )
        )
    rows.sort(key=lambda r: r.updated_at or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    return rows


@router.get("/unread-count", response_model=dict)
def unread_count(
    db: Session = Depends(get_db),
    _: User = Depends(require_hr_or_admin),
):
    total = (
        db.query(Email)
        .filter(
            Email.direction == EmailDirection.INBOUND,
            Email.read_at.is_(None),
        )
        .count()
    )
    return {"unread": total}


@router.post("/conversations/{application_id}/read", response_model=dict)
def mark_conversation_read(
    application_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_hr_or_admin),
):
    db.query(Email).filter(
        Email.application_id == application_id,
        Email.direction == EmailDirection.INBOUND,
        Email.read_at.is_(None),
    ).update(
        {Email.read_at: datetime.now(timezone.utc)},
        synchronize_session=False,
    )
    db.commit()
    return {"ok": True}