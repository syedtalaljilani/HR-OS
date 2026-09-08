import logging
import smtplib
import uuid
from datetime import datetime, timezone
from email.mime.text import MIMEText
from email.utils import formataddr

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models.email import Email
from app.db.models.enums import EmailStatus, EmailType

logger = logging.getLogger("hros.email")


def _friendly_email_type(email_type: EmailType) -> str:
    return email_type.value.replace("_", " ").title()


def record_email(
    db: Session,
    application_id: uuid.UUID | None,
    email_type: EmailType,
    recipient: str,
    subject: str,
    body: str,
    send: bool = True,
) -> Email:
    email = Email(
        application_id=application_id,
        type=email_type,
        recipient=recipient,
        subject=subject,
        status=EmailStatus.PENDING,
    )
    db.add(email)
    db.flush()
    if send:
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
) -> str:
    candidate_name = application.candidate.full_name if application.candidate else "there"
    title = application.job.title if application.job else "the position"
    if email_type == EmailType.SELECTED:
        return (
            f"Dear {candidate_name},\n\n"
            f"Congratulations! We are pleased to inform you that your application "
            f"for {title} is being moved forward in the recruitment process.\n\n"
            "Our HR team will contact you with the next steps.\n\n"
            "Best regards,\nHR OS"
        )
    if email_type == EmailType.REJECTED:
        body = (
            f"Dear {candidate_name},\n\n"
            f"Thank you for applying for {title}. After careful review we regret "
            "to inform you that we will not be moving forward with your application.\n\n"
        )
        if score is not None:
            body += (
                f"Your AI-evaluated profile score: {round(float(score))}/100.\n"
            )
        if rank is not None and total_candidates:
            body += (
                f"You were ranked #{rank} of {total_candidates} candidates who "
                "applied for this position.\n"
            )
        if reason:
            body += f"\nReason: {reason}\n"
        body += (
            "\nWe appreciate the time and effort you invested.\n\n"
            "Best regards,\nHR OS"
        )
        return body
    return (
        f"Dear {candidate_name},\n\n"
        f"Thank you for your application for {title}.\n\n"
        f"Application ID: {application.application_id}\n"
        "Your application is now in review. You will receive an update on your "
        "application status, including the evaluation result, by email.\n\n"
        "Best regards,\nHR OS"
    )