import logging
import re
import smtplib
import urllib.parse
import uuid
from datetime import datetime, timezone
from email.mime.text import MIMEText
from email.utils import formataddr
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models.email import Email
from app.db.models.enums import EmailDirection, EmailStatus, EmailType

logger = logging.getLogger("hros.email")

# Interview times are stored in UTC (the web form converts local wall time to
# UTC before saving), so the candidate-facing email must render them back in
# local time — otherwise a 08:00 PKT interview is announced as 03:00 AM.
HR_TZ = ZoneInfo("Asia/Karachi")


def _friendly_email_type(email_type: EmailType) -> str:
    return email_type.value.replace("_", " ").title()


def _clean_map_query(address: str) -> str:
    """Strip address labels and stray fragments so Google Maps can geocode it.

    Settings values often carry "Head Office:" prefixes or dangling "Plot No,"
    tokens; a raw URL-encoded copy of those makes the map link and embed fail
    to find the place.
    """
    lines = []
    for raw_line in address.splitlines():
        line = raw_line.strip()
        line = re.sub(r"^map\s*:\s*\S+.*$", "", line, flags=re.IGNORECASE).strip()
        line = re.sub(
            r"^(head\s*office|registered\s*office|office|plant|factory|shop|plot|address)\s*[:.\-]+\s*",
            "",
            line,
            flags=re.IGNORECASE,
        ).strip()
        if line:
            lines.append(line)
    cleaned = ", ".join(lines)
    cleaned = re.sub(
        r"(?i)\b(?:head\s*office|registered\s*office|office|plant|factory|shop|plot|address)\s*[:.\-]+\s*",
        "",
        cleaned,
    )
    cleaned = re.sub(r"(?i)\b(?:plot|shop)\s*(?:no\.?)?\s*(?=,|$)", "", cleaned)
    cleaned = re.sub(r"(,\s*)+", ", ", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip(" ,")
    # Collapse repeated identical segments ("Kanzo Ag, Kanzo Ag, …") left over
    # from a duplicated company/office name in the stored address.
    segments = [seg.strip() for seg in cleaned.split(", ") if seg.strip()]
    unique: list[str] = []
    for seg in segments:
        if not unique or seg.lower() != unique[-1].lower():
            unique.append(seg)
    return ", ".join(unique)


def record_email(
    db: Session,
    application_id: uuid.UUID | None,
    email_type: EmailType,
    recipient: str,
    subject: str,
    body: str,
    send: bool = True,
    direction: EmailDirection = EmailDirection.OUTBOUND,
    sender_email: str | None = None,
) -> Email:
    email = Email(
        application_id=application_id,
        type=email_type,
        direction=direction,
        sender_email=sender_email,
        recipient=recipient,
        subject=subject,
        body=body,
        status=EmailStatus.PENDING,
    )
    db.add(email)
    db.flush()
    if send:
        try:
            _deliver(email, body)
        except Exception:
            try:
                _deliver(email, body)
            except Exception:
                email.status = EmailStatus.FAILED
                logger.exception(
                    "Failed to deliver %s email to %s",
                    _friendly_email_type(email.type),
                    email.recipient,
                )
    db.commit()
    db.refresh(email)
    return email


def _deliver(email: Email, body: str) -> None:
    """Send the email over SMTP.

    Falls back to logging when SMTP is not configured so development and
    offline runs keep working.
    """
    if not (
        settings.EMAIL_ENABLED
        and settings.SMTP_USER
        and settings.SMTP_PASSWORD
    ):
        logger.info(
            "SMTP not configured — logging %s email to %s | subject: %s\n%s",
            _friendly_email_type(email.type),
            email.recipient,
            email.subject,
            body[:500],
        )
        email.status = EmailStatus.SENT
        return

    sender = settings.SMTP_FROM or settings.SMTP_USER
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = email.subject
    msg["From"] = formataddr((settings.SMTP_FROM_NAME, sender))
    msg["To"] = email.recipient

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=30) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.sendmail(sender, [email.recipient], msg.as_string())
    email.status = EmailStatus.SENT
    email.sent_at = datetime.now(timezone.utc)
    logger.info(
        "Sent %s email to %s | subject: %s",
        _friendly_email_type(email.type),
        email.recipient,
        email.subject,
    )


def application_email_subject(application, email_type: EmailType) -> str:
    title = application.job.title if application.job else "the position"
    if email_type == EmailType.SELECTED:
        return f"Application Update: You have been selected for {title}"
    if email_type == EmailType.REJECTED:
        return f"Application Update on {title}"
    if email_type == EmailType.INTERVIEW:
        return f"Interview Invitation for {title}"
    if email_type == EmailType.REPLY:
        return f"Re: Application Update for {title}"
    if email_type == EmailType.TALENT_POOL:
        return f"Exciting opportunity matching your profile: {title}"
    return f"Application received for {title}"


def application_email_body(
    application,
    email_type: EmailType,
    reason: str | None = None,
    score: int | float | None = None,
    rank: int | None = None,
    total_candidates: int | None = None,
    interview=None,
    company_location: str | None = None,
    company_name: str | None = None,
    hr_contact: str | None = None,
) -> str:
    candidate_name = application.candidate.full_name if application.candidate else "there"
    title = application.job.title if application.job else "the position"
    signer = hr_contact or settings.HR_NAME or "HR Team"
    company = company_name or settings.COMPANY_NAME
    signoff = f"Best regards,\n{signer}"
    if company:
        signoff += f"\n{company}"
    if email_type == EmailType.SELECTED:
        return (
            f"Dear {candidate_name},\n\n"
            f"Congratulations! We are pleased to inform you that your application "
            f"for {title} is being moved forward in the recruitment process.\n\n"
            "Our HR team will contact you with the next steps.\n\n"
            f"{signoff}"
        )
    if email_type == EmailType.INTERVIEW:
        when = getattr(interview, "scheduled_at", None)
        if isinstance(when, datetime):
            if when.tzinfo is None:
                when = when.replace(tzinfo=timezone.utc)
            when_text = when.astimezone(HR_TZ).strftime(
                "%A, %d %B %Y at %I:%M %p"
            )
        else:
            when_text = "to be confirmed"
        location = getattr(interview, "location", None) or None
        if not location and company_location:
            location = company_location
        notes = getattr(interview, "notes", None)
        body = (
            f"Dear {candidate_name},\n\n"
            f"Thank you for your interest in {title}. Following a careful review "
            "of your application, we would like to invite you to an interview "
            "call with our team.\n\n"
            f"Scheduled for: {when_text}\n"
        )
        if location:
            custom_map_links = re.findall(r"(?im)^map\s*:\s*(\S+)\s*$", location)
            shown_location = _clean_map_query(location)
            if shown_location:
                body += f"Where / how: {shown_location}\n"
            if custom_map_links:
                body += f"Map: {custom_map_links[0]}\n"
            elif shown_location:
                map_url = (
                    "https://www.google.com/maps/search/?api=1&query="
                    + urllib.parse.quote(shown_location)
                )
                body += f"Map (open with pin): {map_url}\n"
        if notes:
            body += f"\nDetails: {notes}\n"
        body += (
            "\nPlease confirm your availability — reply to this email if the "
            "time isn't convenient and we will reschedule.\n\n"
            f"{signoff}"
        )
        return body
    if email_type == EmailType.REJECTED:
        body = (
            f"Dear {candidate_name},\n\n"
            f"Thank you for applying for {title}. After careful review we regret "
            "to inform you that we will not be moving forward with your application.\n\n"
        )
        if reason:
            body += f"Reason: {reason}\n"
        body += (
            "\nWe appreciate the time and effort you invested.\n\n"
            f"{signoff}"
        )
        return body
    return (
        f"Dear {candidate_name},\n\n"
        f"Thank you for your application for {title}.\n\n"
        f"Application ID: {application.application_id}\n"
        "Your application is now in review. You will receive an update on your "
        "application status, including the evaluation result, by email.\n\n"
        f"{signoff}"
    )


def _rebuild_email_body_for(
    application, email_type: EmailType, email: Email
) -> str:
    """Reconstruct an email body from the linked application.

    For REJECTED emails carry over the AI score, rank and the rejection reason
    found in the status history so the original meaning survives a retry.
    """
    score = rank = total_candidates = None
    reason = None

    if email_type == EmailType.REJECTED:
        screening = application.screening_results[-1] if application.screening_results else None
        if screening is not None and screening.score is not None:
            try:
                score = float(screening.score)
            except (TypeError, ValueError):
                pass
        history = sorted(
            (h for h in application.status_history or []),
            key=lambda h: h.created_at,
        )
        for h in reversed(history):
            if h.to_status == "REJECTED" and h.reason:
                reason = h.reason
                break

    return application_email_body(
        application,
        email_type,
        reason=reason,
        score=score,
        rank=rank,
        total_candidates=total_candidates,
    )


def flush_pending_emails(
    db: Session, limit: int = 50
) -> dict:
    """Re-attempt delivery for emails that are stuck in PENDING or FAILED.

    Uses the stored body when available; otherwise regenerates the body from
    the linked application so the proper reason is preserved. Returns a summary
    of delivery attempts.
    """
    from app.db.models.application import Application

    pending = (
        db.query(Email)
        .filter(Email.status.in_([EmailStatus.PENDING, EmailStatus.FAILED]))
        .order_by(Email.created_at.asc())
        .limit(limit)
        .all()
    )

    sent = 0
    failed: list[str] = []
    for email in pending:
        body = email.body
        if not body and email.application_id:
            application = db.get(Application, email.application_id)
            if application is not None:
                body = _rebuild_email_body_for(application, email.type, email)
                email.body = body
        if not body:
            failed.append(f"{email.id}: no body available")
            continue
        try:
            _deliver(email, body)
            sent += 1
        except Exception:
            email.status = EmailStatus.FAILED
            failed.append(f"{email.id}: {email.recipient}")
            logger.exception(
                "Failed to re-deliver %s email to %s",
                _friendly_email_type(email.type),
                email.recipient,
            )

    db.commit()
    return {"attempted": len(pending), "sent": sent, "failed": failed}