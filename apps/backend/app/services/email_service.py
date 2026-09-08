import logging
import uuid

from sqlalchemy.orm import Session

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
        _deliver(email, body)
    db.commit()
    db.refresh(email)
    return email


def _deliver(email: Email, body: str) -> None:
    """Development delivery: logs the email. Swap with Resend/SMTP in production."""
    logger.info(
        "Sending %s email to %s | subject: %s\n%s",
        _friendly_email_type(email.type),
        email.recipient,
        email.subject,
        body[:500],
    )
    email.status = EmailStatus.SENT


def application_email_subject(application, email_type: EmailType) -> str:
    title = application.job.title if application.job else "the position"
    if email_type == EmailType.SELECTED:
        return f"Application Update: You have been selected for {title}"
    if email_type == EmailType.REJECTED:
        return f"Application Update: Update on {title}"
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