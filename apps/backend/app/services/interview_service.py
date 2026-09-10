"""Interview helpers shared by the scheduling routes and the public
candidate reschedule / remote-interview flow.

Candidates reach these flows through a secret per-interview link
(``Interview.reschedule_token``) that is included in the invitation email.
"""
import logging
import uuid
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models.application import Application
from app.db.models.enums import (
    EmailDirection,
    EmailType,
    InterviewRequestStatus,
    InterviewRequestType,
    InterviewStatus,
    InterviewType,
)
from app.db.models.interview import Interview, InterviewRequest
from app.services import audit_service as audit
from app.services import settings_service
from app.services.email_service import (
    application_email_body,
    application_email_subject,
    record_email,
)
from app.utils.tokens import generate_secure_token

logger = logging.getLogger("hros.interview")


def _when_text(when: datetime | None) -> str:
    if isinstance(when, datetime):
        if when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)
        return when.astimezone(ZoneInfo("Asia/Karachi")).strftime(
            "%A, %d %B %Y at %I:%M %p"
        )
    return "to be confirmed"


def as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def generate_reschedule_token() -> str:
    return generate_secure_token()


def default_available_slots(scheduled_at: datetime, count: int = 3) -> list[datetime]:
    """Suggested alternatives: the same wall-clock time on the next weekdays."""
    current = as_utc(scheduled_at)
    slots: list[datetime] = []
    day = current + timedelta(days=1)
    while len(slots) < count:
        while day.weekday() >= 5:  # skip Sat/Sun
            day += timedelta(days=1)
        slots.append(
            day.replace(
                hour=current.hour,
                minute=current.minute,
                second=0,
                microsecond=0,
            )
        )
        day += timedelta(days=1)
    return slots


def setup_reschedule(interview: Interview) -> None:
    """Ensure the interview carries a reschedule token and candidate-facing slots."""
    if not interview.reschedule_token:
        interview.reschedule_token = generate_reschedule_token()
    if not interview.available_slots:
        slots = [as_utc(interview.scheduled_at).isoformat()]
        slots += [s.isoformat() for s in default_available_slots(interview.scheduled_at)]
        interview.available_slots = slots


def interview_slots(interview: Interview) -> list[datetime]:
    raw = interview.available_slots or [as_utc(interview.scheduled_at).isoformat()]
    slots: list[datetime] = []
    for item in raw:
        try:
            slots.append(as_utc(datetime.fromisoformat(str(item))))
        except (TypeError, ValueError):
            continue
    return sorted(set(slots))


def _record_inbound_message(
    db: Session,
    application: Application,
    body: str,
    subject: str | None = None,
) -> None:
    """Record a candidate-originated update in the dashboard chat thread."""
    candidate = application.candidate
    if candidate is None:
        return
    email = record_email(
        db,
        application_id=application.id,
        email_type=EmailType.REPLY,
        recipient=candidate.email,
        sender_email=candidate.email,
        subject=subject or "Update on interview",
        body=body,
        send=False,
        direction=EmailDirection.INBOUND,
    )
    logger.info("recorded candidate interview update in chat: %s", email.id)


def candidate_reschedule(
    db: Session,
    interview: Interview,
    selected_slot: datetime,
) -> Interview:
    """Cancel the previous interview(s) and schedule a new one at the slot the
    candidate picked. Emails the updated invitation and records the change in
    the dashboard chat thread."""
    application = interview.application
    selected_slot = as_utc(selected_slot)
    old_summary = _when_text(interview.scheduled_at)

    scheduled = (
        db.query(Interview)
        .filter(
            Interview.application_id == application.id,
            Interview.status == InterviewStatus.SCHEDULED,
        )
        .all()
    )
    for other in scheduled:
        other.status = InterviewStatus.CANCELLED
    db.flush()

    new = Interview(
        application_id=application.id,
        type=interview.type,
        scheduled_at=selected_slot,
        location=interview.location,
        status=InterviewStatus.SCHEDULED,
    )
    base = (interview.notes or "").strip()
    new.notes = (
        f"{base}\n" if base else ""
    ) + f"[auto] Rescheduled from {old_summary} by the candidate."
    setup_reschedule(new)
    db.add(new)
    db.flush()

    company_name, hr_name, company_location = settings_service.org_identity(db)
    title = application.job.title if application.job else "the position"
    record_email(
        db,
        application_id=application.id,
        email_type=EmailType.INTERVIEW,
        recipient=application.candidate.email,
        subject=application_email_subject(application, EmailType.INTERVIEW),
        body=application_email_body(
            application,
            EmailType.INTERVIEW,
            interview=new,
            company_location=company_location,
            company_name=company_name,
            hr_contact=hr_name,
            reschedule_link=new.reschedule_link,
        ),
        send=True,
    )
    _record_inbound_message(
        db,
        application,
        f'Candidate requested to move the interview from {old_summary} to '
        f'{_when_text(selected_slot)}.',
        subject="Interview reschedule request",
    )
    audit.log_action(
        db,
        user_id=None,
        action="interview.reschedule",
        entity_type="interview",
        entity_id=new.id,
        new_value={
            "application_id": str(application.id),
            "previous_interview": str(interview.id),
            "from": old_summary,
            "to": _when_text(selected_slot),
        },
    )
    db.commit()
    db.refresh(new)
    return new


def upsert_remote_request(
    db: Session,
    interview: Interview,
    reason: str | None,
) -> InterviewRequest:
    """Create (or update) a pending remote-interview request for the candidate."""
    application = interview.application
    rea = (reason or "").strip()
    request = (
        db.query(InterviewRequest)
        .filter(
            InterviewRequest.application_id == application.id,
            InterviewRequest.type == InterviewRequestType.REMOTE,
            InterviewRequest.status == InterviewRequestStatus.PENDING,
        )
        .order_by(InterviewRequest.created_at.desc())
        .first()
    )
    if request is None:
        request = InterviewRequest(
            application_id=application.id,
            interview_id=interview.id,
            type=InterviewRequestType.REMOTE,
            status=InterviewRequestStatus.PENDING,
        )
        db.add(request)
    request.reason = rea or request.reason
    db.flush()

    _record_inbound_message(
        db,
        application,
        f"Candidate requested a remote interview."
        + (f"\nReason: {rea}" if rea else ""),
        subject="Remote interview request",
    )
    audit.log_action(
        db,
        user_id=None,
        action="interview.remote-request",
        entity_type="interview_request",
        entity_id=request.id,
        new_value={"application_id": str(application.id), "reason": rea},
    )
    db.commit()
    db.refresh(request)
    return request


def create_slot_request(
    db: Session,
    interview: Interview,
    *,
    proposed_at: datetime | None,
    awaiting_time: bool,
    reason: str | None,
) -> InterviewRequest:
    """Create (or update) a pending new-date/time request for the candidate.

    Used by the email reply agent's human-in-the-loop flow: when the candidate
    asks for a different interview time, the first email with a date but no time
    is stored as an ``awaiting_time`` request; once the time arrives the request
    is completed (``awaiting_time=False``) and shown to HR for approval.
    """
    application = interview.application
    rea = (reason or "").strip()
    request = (
        db.query(InterviewRequest)
        .filter(
            InterviewRequest.application_id == application.id,
            InterviewRequest.type == InterviewRequestType.NEW_SLOT,
            InterviewRequest.status == InterviewRequestStatus.PENDING,
        )
        .order_by(InterviewRequest.created_at.desc())
        .first()
    )
    if request is None:
        request = InterviewRequest(
            application_id=application.id,
            interview_id=interview.id,
            type=InterviewRequestType.NEW_SLOT,
            status=InterviewRequestStatus.PENDING,
        )
        db.add(request)
    request.interview_id = interview.id
    if proposed_at is not None:
        request.proposed_at = as_utc(proposed_at)
    request.awaiting_time = awaiting_time
    request.reason = rea or request.reason
    db.flush()

    if awaiting_time:
        note = (
            f"Candidate asked to move the interview and gave a date "
            f"{_when_text(request.proposed_at)} but no time yet; the agent asked "
            f"for the time."
        )
    else:
        note = (
            f"Candidate proposed a new interview time: "
            f"{_when_text(request.proposed_at)}."
        )
    _record_inbound_message(db, application, note, subject="New time request")
    audit.log_action(
        db,
        user_id=None,
        action="interview.slot-request",
        entity_type="interview_request",
        entity_id=request.id,
        new_value={
            "application_id": str(application.id),
            "proposed_at": (
                request.proposed_at.isoformat() if request.proposed_at else None
            ),
            "awaiting_time": awaiting_time,
        },
    )
    db.commit()
    db.refresh(request)
    return request


def review_slot_request(
    db: Session,
    request: InterviewRequest,
    *,
    accept: bool,
    resolved_by: uuid.UUID | None = None,
    note: str | None = None,
) -> InterviewRequest:
    """HR approves or declines a candidate's proposed new interview time.

    On accept the interview is rescheduled to the proposed time (previous
    SCHEDULED interviews cancelled) and a fresh invitation email is sent. On
    decline the interview stays as scheduled and the candidate is informed.
    """
    from fastapi import HTTPException, status as http_status

    application = request.application
    interview = request.interview
    candidate = application.candidate
    now = datetime.now(timezone.utc)
    request.status = (
        InterviewRequestStatus.ACCEPTED if accept else InterviewRequestStatus.DECLINED
    )
    request.resolved_by = resolved_by
    request.resolved_at = now

    title = application.job.title if application.job else "the position"
    company_name, hr_name, company_location = settings_service.org_identity(db)

    if accept:
        target = request.proposed_at
        if target is None:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="No proposed time recorded for this request",
            )
        target = as_utc(target)
        if target <= now:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="Proposed time is in the past",
            )

        old_summary = _when_text(interview.scheduled_at) if interview else "the old slot"
        scheduled = (
            db.query(Interview)
            .filter(
                Interview.application_id == application.id,
                Interview.status == InterviewStatus.SCHEDULED,
            )
            .all()
        )
        for other in scheduled:
            other.status = InterviewStatus.CANCELLED
        db.flush()

        new = Interview(
            application_id=application.id,
            type=interview.type if interview else InterviewType.HR,
            scheduled_at=target,
            location=interview.location if interview else None,
            status=InterviewStatus.SCHEDULED,
        )
        new.notes = (
            f"[auto] Candidate proposed {_when_text(target)}; approved by HR "
            f"(from {old_summary})."
        )
        setup_reschedule(new)
        db.add(new)
        db.flush()

        record_email(
            db,
            application_id=application.id,
            email_type=EmailType.INTERVIEW,
            recipient=candidate.email,
            subject=application_email_subject(application, EmailType.INTERVIEW),
            body=application_email_body(
                application,
                EmailType.INTERVIEW,
                interview=new,
                company_location=company_location,
                company_name=company_name,
                hr_contact=hr_name,
                reschedule_link=new.reschedule_link,
            )
            + (f"\n\nNote from HR:\n{note}" if note else ""),
            send=True,
        )
        _record_inbound_message(
            db,
            application,
            f"HR approved the candidate's proposed time: {_when_text(target)}."
            + (f"\nNote: {note}" if note else ""),
            subject="New interview time approved",
        )
        audit.log_action(
            db,
            user_id=resolved_by,
            action="interview.slot-approved",
            entity_type="interview",
            entity_id=new.id,
            new_value={
                "application_id": str(application.id),
                "request_id": str(request.id),
                "from": old_summary,
                "to": _when_text(target),
            },
        )
    else:
        before = _when_text(request.proposed_at) if request.proposed_at else "the proposed time"
        now_text = _when_text(interview.scheduled_at) if interview else "as confirmed earlier"
        body = (
            f"Dear {candidate.full_name},\n\n"
            f"Regarding your request to move the interview for {title} to "
            f"{before}: we are unable to accommodate that time. Your interview "
            f"remains scheduled for {now_text} as confirmed earlier.\n\n"
            "If you need a different time, use the reschedule link in your "
            "previous email.\n\n"
            + (f"Note from HR:\n{note}\n\n" if note else "")
            + "Best regards,\n"
            f"{hr_name or 'HR Team'}"
        )
        record_email(
            db,
            application_id=application.id,
            email_type=EmailType.INTERVIEW,
            recipient=candidate.email,
            subject=f"Update on your interview for {title}",
            body=body,
            send=True,
        )
        audit.log_action(
            db,
            user_id=resolved_by,
            action="interview.slot-declined",
            entity_type="interview_request",
            entity_id=request.id,
            new_value={
                "application_id": str(application.id),
                "proposed_at": request.proposed_at.isoformat()
                if request.proposed_at
                else None,
            },
        )

    db.commit()
    db.refresh(request)
    return request


def review_remote_request(
    db: Session,
    request: InterviewRequest,
    *,
    accept: bool,
    meeting_link: str | None,
    resolved_by: uuid.UUID | None = None,
    note: str | None = None,
) -> InterviewRequest:
    """HR accepts or declines a candidate's remote-interview request."""
    application = request.application
    interview = request.interview
    candidate = application.candidate
    now = datetime.now(timezone.utc)
    request.status = (
        InterviewRequestStatus.ACCEPTED if accept else InterviewRequestStatus.DECLINED
    )
    request.resolved_by = resolved_by
    request.resolved_at = now

    title = application.job.title if application.job else "the position"
    company_name, hr_name, company_location = settings_service.org_identity(db)

    if accept:
        link = (meeting_link or "").strip()
        if link:
            interview.location = link
        subject = f"Remote Interview Confirmed for {title}"
        body = application_email_body(
            application,
            EmailType.INTERVIEW,
            interview=interview,
            company_location=company_location,
            company_name=company_name,
            hr_contact=hr_name,
            reschedule_link=interview.reschedule_link,
        )
        if note:
            body += f"\n\nNote from HR:\n{note}"
    else:
        subject = f"Update on your interview for {title}"
        body = (
            f"Dear {candidate.full_name},\n\n"
            f"Regarding your request for a remote interview for {title}: we were "
            "unable to arrange it at this time. Your interview remains scheduled "
            f"for {_when_text(interview.scheduled_at)} as confirmed earlier.\n\n"
            "If you need a different time, use the reschedule link in your "
            "previous email.\n\n"
            "Best regards,\n"
            f"{hr_name or 'HR Team'}"
        )

    record_email(
        db,
        application_id=application.id,
        email_type=EmailType.INTERVIEW,
        recipient=candidate.email,
        subject=subject,
        body=body,
        send=True,
    )
    audit.log_action(
        db,
        user_id=resolved_by,
        action=(
            "interview.remote-accepted"
            if accept
            else "interview.remote-declined"
        ),
        entity_type="interview_request",
        entity_id=request.id,
        new_value={
            "application_id": str(application.id),
            "meeting_link": meeting_link,
            "note": note,
        },
    )
    db.commit()
    db.refresh(request)
    return request