"""Email reply agent.

- When a candidate emails the company with a query, an AI-drafted answer is
  recorded and delivered, using the candidate's application details and the
  scheduled interview (when pending) as context. Automated out-of-office /
  bounce messages are ignored so the agent never argues with a bot loop.
- Interviews whose scheduled time passed without attendance are marked missed
  and the candidate is re-invited.
- When an application becomes SELECTED or SHORTLISTED, every remaining
  SCHEDULED interview of that candidate is cancelled.
- When IMAP is configured, candidate email replies are fetched automatically,
  recorded in the dashboard chat, and answered by the agent.

A background loop (``start_scheduler``) runs the automatic checks periodically;
it only acts while emailing is enabled.
"""
import email as email_parser
import imaplib
import logging
import re
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models.application import Application
from app.db.models.candidate import Candidate
from app.db.models.email import Email
from app.db.models.enums import (
    EmailDirection,
    EmailStatus,
    EmailType,
    InterviewRequestStatus,
    InterviewRequestType,
    InterviewStatus,
)
from app.db.models.interview import Interview, InterviewRequest
from app.services import audit_service as audit
from app.services import email_agent_service
from app.services.email_service import record_email
from app.services.interview_service import as_utc, create_slot_request
from app.services.slot_parser import build_proposed_at, extract_requested_slot

logger = logging.getLogger("hros.reply-agent")


def _format_when(when: datetime | None) -> str:
    if isinstance(when, datetime):
        if when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)
        return when.astimezone(ZoneInfo("Asia/Karachi")).strftime(
            "%A, %d %B %Y at %I:%M %p"
        )
    return "to be confirmed"


def _interview_time_hr_notes(interview: Interview) -> str:
    application = interview.application
    candidate = application.candidate
    title = application.job.title if application.job else "the position"
    parts = [
        f"Interview for {title}."
    ]
    parts.append(f"Interview was scheduled for {_format_when(interview.scheduled_at)}.")
    if interview.location:
        parts.append(f"Interview location / how: {interview.location}.")
    return " ".join(parts)


def _reschedule_link(interview: "Interview | None") -> str | None:
    token = getattr(interview, "reschedule_token", None)
    if token:
        return f"{settings.PUBLIC_BASE_URL.rstrip('/')}/reschedule/{token}"
    return None


def _append_reschedule_link(body: str, interview: "Interview | None") -> str:
    link = _reschedule_link(interview)
    if not link:
        return body
    return (body or "") + f"\n\nNeed a different time? Pick another slot here:\n{link}"


def _open_awaiting_request(
    db: Session, application: Application
) -> InterviewRequest | None:
    return (
        db.query(InterviewRequest)
        .filter(
            InterviewRequest.application_id == application.id,
            InterviewRequest.type == InterviewRequestType.NEW_SLOT,
            InterviewRequest.status == InterviewRequestStatus.PENDING,
            InterviewRequest.awaiting_time.is_(True),
        )
        .order_by(InterviewRequest.created_at.desc())
        .first()
    )


def _draft_slot_reply(
    db: Session,
    candidate: Candidate,
    job_title: str | None,
    *,
    kind: str,
    request: InterviewRequest,
    interview: Interview,
) -> dict:
    current = _format_when(interview.scheduled_at)
    if kind == "ask_time":
        day = (
            request.proposed_at.astimezone(ZoneInfo("Asia/Karachi")).strftime(
                "%A, %d %B"
            )
            if request.proposed_at
            else "that day"
        )
        hr_notes = (
            "The candidate asked to move their interview but did NOT give a time yet "
            f"(they mentioned the date {day}). The current interview is {current} "
            f"for {job_title or 'the position'}. Reply briefly and warmly and ONLY ask "
            "what time works best on that date (one working example such as 03:00 PM). "
            "Do NOT confirm or change anything yet."
        )
        fallback_subject = "Re: your interview time"
        fallback_body = (
            f"Thank you for letting us know about the date change.\n\n"
            f"Which time works best for you on {day}? For example 03:00 PM or "
            f"04:30 PM — once we have the exact time we will confirm it with you.\n\n"
            "Best regards,\nHR Team"
        )
    else:
        when = _format_when(request.proposed_at)
        hr_notes = (
            "Forward the candidate's request to move the interview to "
            f"{when} for {job_title or 'the position'} for HR approval. Reply briefly "
            "and warmly, acknowledging the request and saying it has been forwarded to "
            "the hiring team who will confirm soon."
        )
        fallback_subject = "Re: your interview time"
        fallback_body = (
            f"Thank you for the time you suggested.\n\n"
            f"We have noted your request for {when} and forwarded it to the hiring "
            "team for confirmation. You will receive a confirmation shortly.\n\n"
            "Best regards,\nHR Team"
        )
    try:
        draft = email_agent_service.draft_email(
            email_type="REPLY",
            candidate_name=candidate.full_name,
            job_title=job_title,
            context={
                "INTERVIEW_TIME": when if kind != "ask_time" else current,
                "INTERVIEW_LOCATION": interview.location
                or settings.COMPANY_LOCATION
                or "to be announced",
            },
            hr_notes=hr_notes,
            db=db,
        )
        return {
            "subject": draft.get("subject") or fallback_subject,
            "body": draft.get("body") or fallback_body,
        }
    except Exception:
        logger.exception("slot reply draft failed; using fallback template")
        return {"subject": fallback_subject, "body": fallback_body}


def _handle_slot_request(
    db: Session,
    *,
    application: Application,
    interview: Interview,
    candidate: Candidate,
    slot: dict,
    query: str,
    job_title: str | None,
) -> dict | None:
    has_date = slot.get("date") is not None
    has_time = slot.get("time") is not None

    if has_date and not has_time:
        request = create_slot_request(
            db,
            interview,
            proposed_at=build_proposed_at(slot),
            awaiting_time=True,
            reason=query,
        )
        draft = _draft_slot_reply(
            db, candidate, job_title, kind="ask_time", request=request, interview=interview
        )
    elif has_time:
        ctx_date = slot.get("date")
        if ctx_date is None:
            pending = _open_awaiting_request(db, application)
            if pending is None or pending.proposed_at is None:
                return None
            ctx_date = pending.proposed_at.astimezone(
                ZoneInfo("Asia/Karachi")
            ).date()
        proposed = build_proposed_at({"date": ctx_date, "time": slot["time"]})
        if proposed is None:
            return None
        request = create_slot_request(
            db,
            interview,
            proposed_at=proposed,
            awaiting_time=False,
            reason=query,
        )
        draft = _draft_slot_reply(
            db, candidate, job_title, kind="forwarded", request=request, interview=interview
        )
    else:
        return None

    reply_subject = draft["subject"]
    if reply_subject and not reply_subject.lower().startswith(("re:", "re ")):
        reply_subject = f"Re: {reply_subject}"
    email = record_email(
        db,
        application_id=application.id,
        email_type=EmailType.REPLY,
        recipient=candidate.email,
        subject=reply_subject or "Re: your interview time",
        body=_append_reschedule_link(draft["body"], interview),
        send=True,
    )
    db.commit()
    return {
        "note": "Slot request handled by the agent.",
        "candidate_name": candidate.full_name,
        "application_id": str(application.id),
        "interview_id": str(interview.id),
        "awaiting_time": request.awaiting_time,
        "proposed_at": (
            request.proposed_at.isoformat() if request.proposed_at else None
        ),
        "email_id": str(email.id),
        "subject": email.subject,
        "body": email.body,
    }


_AUTO_BOUNCE_HINTS = (
    "out of office",
    "ooa:",
    "autoreply",
    "auto-reply",
    "auto reply",
    "mail delivery",
    "delivery status",
    "undeliverable",
    "returned mail",
    "vacation",
    "away from my desk",
    "mailer-daemon",
)


def _is_auto_or_bounce(subject: str | None, text: str | None) -> bool:
    haystack = f"{subject or ''} {text or ''}".lower()
    return any(hint in haystack for hint in _AUTO_BOUNCE_HINTS)


def _store_inbound(
    db: Session,
    *,
    application_id: uuid.UUID | None,
    candidate_email: str,
    subject: str | None,
    text: str | None,
) -> Email | None:
    """Persist the candidate's message so the dashboard chat thread shows it."""
    subject_key = (subject or "").strip() or "(no subject)"
    body_key = (text or "").strip() or None
    exists = (
        db.query(Email.id)
        .filter(
            Email.recipient == candidate_email,
            Email.direction == EmailDirection.INBOUND,
            Email.subject == subject_key,
            Email.body == body_key,
        )
        .first()
    )
    if exists is not None:
        return None  # same message already recorded
    email = Email(
        application_id=application_id,
        type=EmailType.REPLY,
        direction=EmailDirection.INBOUND,
        sender_email=candidate_email,
        recipient=candidate_email,
        subject=subject_key,
        body=body_key,
        status=EmailStatus.SENT,
        sent_at=datetime.now(timezone.utc),
    )
    db.add(email)
    db.flush()
    return email


def _clean_query(text: str | None) -> str:
    """Strip quoted reply chains, forwarded headers and signatures out of a
    candidate message so the AI answers the actual question, not the history."""
    if not text:
        return (text or "").strip()
    kept: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            if kept:
                kept.append("")
            continue
        if stripped.startswith(">"):
            continue
        if re.match(r"^On .+wrote:$", stripped):
            continue
        if re.match(r"^(From|Sent|To|Cc|Bcc|Reply-To):", stripped):
            continue
        if re.match(r"^(Subject|Date):", stripped):
            continue
        if re.match(r"^-{2,}\s*.*(Original Message|Forwarded message|Reply Above|type your reply)", stripped):
            continue
        kept.append(stripped)
    cleaned = re.sub(r"\n{3,}", "\n\n", "\n".join(kept)).strip()
    return cleaned or (text or "").strip()


def handle_reply(
    db: Session,
    *,
    from_email: str,
    subject: str | None = None,
    text: str | None = None,
) -> dict:
    """Answer a candidate's email query with an AI-drafted reply.

    Any query from a known candidate is answered: the draft draws on the
    candidate's application details and, when one is pending, the scheduled
    interview so timing/venue questions can be answered directly. Automated
    (out-of-office / bounce) messages are ignored so the agent never argues
    with a bot loop.
    """
    sender = (from_email or "").strip().lower()
    if not sender:
        return {"note": "No sender email provided."}

    if _is_auto_or_bounce(subject, text):
        return {"note": "Automated / bounce message — no reply sent."}

    candidate = db.query(Candidate).filter(Candidate.email == sender).first()
    if candidate is None:
        return {"note": "No candidate found for the sender email."}

    now = datetime.now(timezone.utc)
    interview = (
        db.query(Interview)
        .join(Application, Interview.application_id == Application.id)
        .filter(
            Application.candidate_id == candidate.id,
            Interview.status == InterviewStatus.SCHEDULED,
            Interview.scheduled_at
            >= now - timedelta(minutes=settings.MISSED_INTERVIEW_GRACE_MINUTES),
        )
        .order_by(Interview.scheduled_at.asc())
        .first()
    )
    application = interview.application if interview else None
    if application is None:
        application = (
            db.query(Application)
            .filter(
                Application.candidate_id == candidate.id,
                Application.deleted_at.is_(None),
            )
            .order_by(Application.created_at.desc())
            .first()
        )

    clean_text = _clean_query(text)

    stored = _store_inbound(
        db,
        application_id=application.id if application else None,
        candidate_email=candidate.email,
        subject=subject,
        text=clean_text,
    )
    if stored is None:
        # Same sender + subject + body was already imported earlier. The
        # (date-based) IMAP search can re-match the same message on the next
        # tick, so do NOT draft or send a second reply for it.
        db.rollback()
        return {"note": "Duplicate message — already recorded, no reply sent."}
    # Persist the candidate's message immediately: even if AI drafting or the
    # outbound send below fails, the inbound message still shows in the chat
    # thread instead of being rolled back with the rest of the transaction.
    db.commit()

    query = clean_text or (subject or "").strip()
    job_title = application.job.title if application and application.job else None
    context: dict[str, str] = {}
    if application and application.job:
        context["JOB_TITLE"] = job_title or ""
    if interview is not None:
        context["INTERVIEW_TIME"] = _format_when(interview.scheduled_at)
        if interview.location:
            context["INTERVIEW_LOCATION"] = interview.location

    # Human-in-the-loop slot requests: when the candidate asks to move the
    # interview and states a date, the agent first asks for the time (no request
    # yet) and only once a full date + time is known does it generate a
    # PENDING request that HR approves from the dashboard.
    slot = extract_requested_slot(query, now=now)
    if slot["intent"] and interview is not None and application is not None:
        handled = _handle_slot_request(
            db,
            application=application,
            interview=interview,
            candidate=candidate,
            slot=slot,
            query=query,
            job_title=job_title,
        )
        if handled:
            return handled

    draft = email_agent_service.draft_email(
        email_type="REPLY",
        candidate_name=candidate.full_name,
        job_title=job_title,
        context=context or None,
        hr_notes=(
            "The candidate just wrote back. Answer exactly what they asked in "
            "their most recent message below. Do NOT repeat the whole interview "
            "invitation wording unless they actually ask for the details again. "
            "You have the context (job title, interview time/location) so you can "
            "confirm a specific time/venue, reschedule, or answer timing questions "
            "accurately and briefly. If their message has no real question, confirm "
            "their reply politely in one or two sentences. If you cannot answer, say "
            "the query was forwarded to the hiring team. Keep it short, warm, and in "
            "the language of their message.\n\n"
            f"CANDIDATE'S MESSAGE:\n{query or '(no text provided)'}"
        ),
        db=db,
    )

    reply_subject = draft["subject"] or "Re: your query"
    if subject and not reply_subject.lower().startswith(("re:", "re ")):
        reply_subject = f"Re: {reply_subject}"

    email = record_email(
        db,
        application_id=application.id if application else None,
        email_type=EmailType.REPLY,
        recipient=candidate.email,
        subject=reply_subject,
        body=_append_reschedule_link(draft["body"], interview),
        send=True,
    )
    return {
        "note": "Reply sent to the candidate.",
        "candidate_name": candidate.full_name,
        "application_id": str(application.id) if application else None,
        "interview_id": str(interview.id) if interview else None,
        "interview_scheduled_at": _format_when(interview.scheduled_at)
        if interview
        else None,
        "email_id": str(email.id),
        "subject": email.subject,
        "body": email.body,
    }


def process_missed_interviews(
    db: Session, *, grace_minutes: int | None = None
) -> dict:
    """Mark past SCHEDULED interviews as missed and re-invite the candidate."""
    grace = (
        grace_minutes
        if grace_minutes is not None
        else settings.MISSED_INTERVIEW_GRACE_MINUTES
    )
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=grace)
    missed = (
        db.query(Interview)
        .filter(
            Interview.status == InterviewStatus.SCHEDULED,
            Interview.scheduled_at <= cutoff,
        )
        .order_by(Interview.scheduled_at.asc())
        .all()
    )

    processed: list[dict] = []
    for interview in missed:
        application = interview.application
        candidate = application.candidate

        interview.status = InterviewStatus.CANCELLED
        note = (
            f"[auto] Candidate missed the interview "
            f"({_format_when(interview.scheduled_at)}); re-invite sent at "
            f"{datetime.now(timezone.utc).isoformat()}."
        )
        if interview.notes:
            interview.notes = f"{interview.notes}\n{note}"
        else:
            interview.notes = note

        audit.log_action(
            db,
            user_id=None,
            action="interview.missed",
            entity_type="interview",
            entity_id=interview.id,
            new_value={
                "application_id": str(application.id),
                "scheduled_at": _format_when(interview.scheduled_at),
                "action_taken": "interview missed and candidate re-invited",
            },
        )

        if candidate is not None:
            draft = email_agent_service.draft_email(
                email_type="INTERVIEW",
                candidate_name=candidate.full_name,
                job_title=application.job.title if application.job else None,
                context={
                    "INTERVIEW_TIME": _format_when(interview.scheduled_at),
                    "INTERVIEW_LOCATION": interview.location
                    or settings.COMPANY_LOCATION
                    or "to be announced",
                },
                hr_notes=(
                    _interview_time_hr_notes(interview)
                    + " The candidate missed this interview. Write a polite "
                    "re-invitation acknowledging they missed it and inviting "
                    "them to re-schedule at a date and time of their choice. "
                    "Ask them to confirm they can attend."
                ),
                db=db,
            )
            record_email(
                db,
                application_id=application.id,
                email_type=EmailType.INTERVIEW,
                recipient=candidate.email,
                subject=draft["subject"],
                body=draft["body"],
                send=True,
            )

        processed.append(
            {
                "interview_id": str(interview.id),
                "application_id": str(application.id),
                "candidate": candidate.full_name if candidate else None,
                "scheduled_at": _format_when(interview.scheduled_at),
            }
        )

    db.commit()
    return {"processed": processed}


def cancel_candidate_pending_interviews(
    db: Session,
    candidate_id: uuid.UUID,
    *,
    changed_by: uuid.UUID | None,
    reason: str,
) -> list[dict]:
    """Cancel every remaining SCHEDULED interview of a candidate (used on hire)."""
    pending = (
        db.query(Interview)
        .join(Application, Interview.application_id == Application.id)
        .filter(
            Application.candidate_id == candidate_id,
            Interview.status == InterviewStatus.SCHEDULED,
        )
        .order_by(Interview.scheduled_at.asc())
        .all()
    )

    cancelled: list[dict] = []
    for interview in pending:
        interview.status = InterviewStatus.CANCELLED
        note = (
            f"[auto] Candidate selected — interview cancelled ({reason}) at "
            f"{datetime.now(timezone.utc).isoformat()}."
        )
        if interview.notes:
            interview.notes = f"{interview.notes}\n{note}"
        else:
            interview.notes = note

        audit.log_action(
            db,
            user_id=changed_by,
            action="interview.cancelled",
            entity_type="interview",
            entity_id=interview.id,
            new_value={
                "candidate_id": str(candidate_id),
                "application_id": str(interview.application_id),
                "reason": reason,
            },
        )
        cancelled.append(
            {
                "interview_id": str(interview.id),
                "application_id": str(interview.application_id),
            }
        )

    db.commit()
    return cancelled


def _extract_address(raw: str) -> str | None:
    """Pull the plain e-mail address out of a "Name <mail@x>" header."""
    if not raw:
        return None
    match = re.search(r"<([^<>]+)>", raw) or re.search(r"[\w.+-]+@[\w.-]+\.[\w.]+", raw)
    return match.group(1).strip().lower() if match else None


def _decode_part(part) -> str:
    payload = part.get_payload(decode=True)
    if payload is None:
        return ""
    text = payload.decode(part.get_content_charset() or "utf-8", errors="replace")
    if part.get_content_type() == "text/html":
        text = re.sub(r"(?is)<(style|script)[^>]*>.*?</\1>", " ", text)
        text = re.sub(r"(?is)<[^>]+>", " ", text)
    return re.sub(r"[ \t]+", " ", text).strip()


def _message_text(parsed) -> str:
    """Return the plain-text body of an e-mail (fall back to HTML, stripped)."""
    if parsed.is_multipart():
        text_parts: list[str] = []
        html_parts: list[str] = []
        for part in parsed.walk():
            ctype = part.get_content_type()
            cdisp = part.get_content_disposition() or ""
            if cdisp.lower() == "attachment":
                continue
            content = _decode_part(part)
            if ctype == "text/plain":
                text_parts.append(content)
            elif ctype == "text/html" and content:
                html_parts.append(content)
        if text_parts:
            return "\n".join(text_parts).strip()
        return "\n".join(html_parts).strip()
    return _decode_part(parsed)


def _or_chain(keys: list[tuple[str, str]]) -> str:
    """Nested IMAP ``OR`` over (header, value) pairs, e.g. ``(OR (FROM a) (FROM b))``."""

    def _term(header: str, value: str) -> str:
        # IMAP quoted strings must not contain quotes or backslashes; drop any
        # control/odd characters so a stray AI-generated subject can't break
        # the whole SEARCH command.
        safe = "".join(ch for ch in value if ch.isprintable() and ch not in '"\\').strip()
        return f'({header} "{safe}")' if safe else ""

    terms = [_term(header, value) for header, value in keys]
    terms = [t for t in terms if t]
    if not terms:
        return ""
    expr = terms[0]
    for term in terms[1:]:
        expr = f"(OR {expr} {term})"
    return expr


def _inbox_filters(db: Session) -> str:
    """IMAP search clause that only matches our candidates' messages.

    Matches (a) any reply to an email we sent recently (by subject) or (b) any
    message from a known candidate — so a busy personal inbox with thousands of
    unseen newsletters/newsletter threads is left completely untouched.

    The window is date-based, not UNSEEN-based: a candidate who read (and Gmail
    auto-marked as Seen) their reply should still show up in the dashboard chat.
    Deduplication in ``_store_inbound`` makes old, already-fetched messages a
    no-op.
    """
    window_days = 30
    since = datetime.now(timezone.utc) - timedelta(days=window_days)
    since_criteria = since.strftime("%d-%b-%Y")
    candidate_emails = [
        row[0].lower()
        for row in db.query(Candidate.email)
        .filter(Candidate.email.isnot(None), Candidate.deleted_at.is_(None))
        .all()
        if row[0] and row[0].strip()
    ]
    # Unique, most-recent subjects only — Gmail rejects SEARCH commands that get
    # too big, so we never let the OR-chain grow past a safe budget.
    seen: set[str] = set()
    unique_subjects: list[str] = []
    for (subject,) in (
        db.query(Email.subject)
        .filter(
            Email.direction == EmailDirection.OUTBOUND,
            Email.created_at >= since,
        )
        .order_by(Email.created_at.desc())
        .all()
    ):
        subject = (subject or "").strip()
        if not subject or subject.lower() in seen:
            continue
        seen.add(subject.lower())
        unique_subjects.append(subject)

    budget = 800
    subjects: list[str] = []
    for subject in unique_subjects:
        cost = len(subject) + 12
        if sum(len(s) for s in subjects) + cost > budget or len(subjects) >= 40:
            break
        subjects.append(subject)

    parts: list[str] = []
    if candidate_emails:
        parts.append(
            _or_chain([("FROM", address) for address in candidate_emails[:200]])
        )
    if subjects:
        parts.append(
            _or_chain([("SUBJECT", subject) for subject in subjects])
        )
    if not parts:
        return "UNSEEN"
    expr = parts[0]
    for part in parts[1:]:
        expr = f"(OR {expr} {part})"
    return f"(SINCE {since_criteria} {expr})"


def fetch_mailbox(db: Session) -> dict:
    """Pull candidate messages from IMAP, feed each to the reply agent.

    Only messages that are replies to our sent emails or that came from a known
    candidate are fetched; everything else in the mailbox is left untouched.
    Returns a summary of what was processed.
    """
    if not (settings.IMAP_ENABLED and settings.EMAIL_ENABLED):
        return {"enabled": False, "processed": [], "summaries": []}

    user = settings.IMAP_USER or settings.SMTP_USER
    password = settings.IMAP_PASSWORD or settings.SMTP_PASSWORD
    if not (user and password):
        logger.warning("IMAP enabled but no credentials configured")
        return {"enabled": True, "processed": [], "summaries": []}

    summaries: list[dict] = []
    try:
        with imaplib.IMAP4_SSL(settings.IMAP_HOST, settings.IMAP_PORT) as conn:
            conn.login(user, password)
            conn.select(settings.IMAP_FOLDER)
            try:
                _, data = conn.search(None, _inbox_filters(db))
            except Exception:
                logger.exception("IMAP SEARCH failed")
                return {"enabled": True, "processed": [], "summaries": []}
            ids = (data[0] or b"").split()

            # Safety cap per pass so a flood of old replies is drained gradually.
            max_per_pass = 25
            if len(ids) > max_per_pass:
                logger.info(
                    "IMAP found %s matching messages; processing the first %s",
                    len(ids),
                    max_per_pass,
                )
                ids = ids[:max_per_pass]

            for message_id in ids:
                try:
                    _, msg_data = conn.fetch(message_id, "(RFC822)")
                    raw = None
                    for part in msg_data:
                        if isinstance(part, tuple):
                            raw = part[1]
                            break
                    if not raw:
                        conn.store(message_id, "+FLAGS", "\\Seen")
                        continue
                    parsed = email_parser.message_from_bytes(raw)
                    from_raw = _extract_address(str(parsed.get("From", "")))
                    subject = str(parsed.get("Subject", "")).strip()
                    body = _message_text(parsed)

                    if from_raw and from_raw.lower() == user.lower():
                        conn.store(message_id, "+FLAGS", "\\Seen")
                        continue  # our own sent copy

                    if from_raw:
                        summary = handle_reply(
                            db,
                            from_email=from_raw,
                            subject=subject or None,
                            text=body or None,
                        )
                        summaries.append(summary)
                    else:
                        summaries.append(
                            {"note": "Message has no sender address — skipped."}
                        )
                    conn.store(message_id, "+FLAGS", "\\Seen")
                    db.commit()
                except Exception:
                    logger.exception("IMAP message processing failed")
                    db.rollback()
                    try:
                        conn.store(message_id, "+FLAGS", "\\Seen")
                    except Exception:
                        pass
        db.commit()
    except Exception:
        logger.exception("IMAP fetch failed")
        db.rollback()
        return {"enabled": True, "processed": [], "summaries": []}

    return {"enabled": True, "processed": summaries, "summaries": summaries}


def send_interview_reminders(db: Session) -> dict:
    """Send a single reminder email to each upcoming interview, ~24h ahead.

    Each interview is reminded at most once (tracked with
    ``Interview.reminder_sent_at``). Interviews scheduled sooner than 24h in
    advance are reminded on the next tick, so candidates always get exactly one
    follow-up before their interview. Already-cancelled or past interviews are
    never reminded.
    """
    from app.db.models.interview import Interview

    now = datetime.now(timezone.utc)
    window_start = now - timedelta(hours=24)
    due = (
        db.query(Interview)
        .filter(
            Interview.status == InterviewStatus.SCHEDULED,
            Interview.reminder_sent_at.is_(None),
            Interview.scheduled_at > now,
            Interview.scheduled_at >= window_start,
        )
        .order_by(Interview.scheduled_at.asc())
        .all()
    )

    processed: list[dict] = []
    for interview in due:
        application = interview.application
        candidate = application.candidate
        if candidate is None:
            continue
        job_title = application.job.title if application.job else None

        draft = email_agent_service.draft_email(
            email_type="INTERVIEW",
            candidate_name=candidate.full_name,
            job_title=job_title,
            context={
                "INTERVIEW_TIME": _format_when(interview.scheduled_at),
                "INTERVIEW_LOCATION": interview.location
                or settings.COMPANY_LOCATION
                or "to be announced",
            },
            hr_notes=(
                _interview_time_hr_notes(interview)
                + " This is the day before the interview. Write a short, warm "
                "interview REMINDER: confirm the time and location from the "
                "context, tell the candidate they can reply here if they need "
                "to reschedule, and ask them to confirm they will attend. One "
                "clear paragraph is enough — do not repeat the whole invitation."
            ),
            db=db,
        )

        record_email(
            db,
            application_id=application.id,
            email_type=EmailType.INTERVIEW,
            recipient=candidate.email,
            subject=f"Interview Reminder for {job_title or 'your interview'}",
            body=_append_reschedule_link(draft["body"], interview),
            send=True,
        )
        interview.reminder_sent_at = now
        audit.log_action(
            db,
            user_id=None,
            action="interview.reminder",
            entity_type="interview",
            entity_id=interview.id,
            new_value={
                "application_id": str(application.id),
                "scheduled_at": _format_when(interview.scheduled_at),
                "reminded_at": now.isoformat(),
            },
        )
        processed.append(
            {
                "interview_id": str(interview.id),
                "application_id": str(application.id),
                "candidate": candidate.full_name,
                "scheduled_at": _format_when(interview.scheduled_at),
            }
        )
        db.commit()

    return {"processed": processed}


def run_auto_agent(db: Session) -> dict:
    """Periodic maintenance: catch missed interviews, fetch replies, flush mail."""
    from app.services.email_service import flush_pending_emails

    missed = process_missed_interviews(db)
    reminders = send_interview_reminders(db)
    inbox = fetch_mailbox(db)
    delivery = flush_pending_emails(db)
    return {
        "missed": missed,
        "reminders": reminders,
        "inbox": inbox,
        "delivery": delivery,
    }


def _scheduler_body() -> None:
    from app.db.session import SessionLocal

    while True:
        time.sleep(settings.REPLY_AGENT_INTERVAL_SECONDS)
        if not (settings.REPLY_AGENT_ENABLED and settings.EMAIL_ENABLED):
            continue
        try:
            with SessionLocal() as db:
                summary = run_auto_agent(db)
            inbox = summary["inbox"]
            logger.info(
                "reply-agent tick: %s missed interview(s), %s reminder(s) sent, "
                "%s inbox message(s), %s email(s) flushed",
                len(summary["missed"]["processed"]),
                len(summary["reminders"]["processed"]),
                len(inbox["processed"]) if inbox.get("enabled") else -1,
                summary["delivery"]["sent"],
            )
        except Exception:
            logger.exception("reply-agent tick failed")


def start_scheduler() -> None:
    """Start the background reply-agent loop (idempotent-ish daemon thread)."""
    threading.Thread(target=_scheduler_body, daemon=True, name="reply-agent").start()