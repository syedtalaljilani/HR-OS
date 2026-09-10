import hashlib
import re
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models.application import (
    Application,
    ApplicationStatusHistory,
    ApplicationTrackingToken,
    CVDocument,
)
from app.db.models.candidate import Candidate
from app.db.models.enums import ApplicationStatus, ExtractionStatus
from app.db.models.job import Job
from app.schemas.application import ApplicationCreate
from app.services import file_service
from app.utils.tokens import generate_secure_token, hash_token
from app.utils.validators import validate_cv_file, validate_file_size


def generate_application_id(db: Session) -> str:
    year = datetime.now(timezone.utc).year
    prefix = f"APP-{year}%"
    last = (
        db.query(func.max(Application.application_id))
        .filter(Application.application_id.like(prefix))
        .scalar()
    )
    if last and last.startswith(f"APP-{year}-"):
        seq = int(last.split("-", 2)[2]) + 1
    else:
        seq = 1
    return f"APP-{year}-{seq:05d}"


def _form_profile(data: ApplicationCreate) -> dict:
    """Build a candidate profile dict from the user-confirmed form fields.

    Starts with the full dynamic profile (all CV-driven sections) sent as JSON,
    then lets the individual form fields override the core sections.
    """
    import json

    profile: dict = {}
    if data.profile_data:
        try:
            parsed = json.loads(data.profile_data)
        except (ValueError, TypeError):
            parsed = None
        if isinstance(parsed, dict):
            profile = parsed
    if data.skills:
        skills = [s.strip() for s in data.skills.split(",") if s.strip()]
        if skills:
            profile["skills"] = skills
    for key in ("education", "experience"):
        raw = getattr(data, key)
        if not raw:
            continue
        try:
            parsed = json.loads(raw)
        except (ValueError, TypeError):
            continue
        if isinstance(parsed, list) and parsed:
            profile[key] = parsed
    return profile


def get_or_create_candidate(
    db: Session, data: ApplicationCreate
) -> Candidate:
    email = data.email.lower()
    candidate = db.query(Candidate).filter(Candidate.email == email).first()
    if candidate is not None and candidate.deleted_at is not None:
        candidate = None
    form_profile = _form_profile(data)
    if candidate:
        if form_profile:
            merged = candidate.profile_data or {}
            merged.update(form_profile)
            candidate.profile_data = merged
        return candidate
    candidate = Candidate(
        full_name=data.full_name,
        email=email,
        phone=data.phone,
        address=data.address,
        profile_data=form_profile or None,
    )
    db.add(candidate)
    try:
        db.flush()
    except IntegrityError:
        # A row for this email already exists (e.g. it was soft-deleted or a
        # concurrent submit inserted it between our SELECT and INSERT). Reuse
        # the existing row instead of failing the whole request with a 500.
        db.rollback()
        candidate = db.query(Candidate).filter(Candidate.email == email).first()
        if candidate is None:
            raise
        if candidate.deleted_at is not None:
            candidate.deleted_at = None
        db.flush()
    return candidate


def _normalize_phone(phone: str | None) -> str:
    if not phone:
        return ""
    return re.sub(r"[^\d]", "", phone).lstrip("0")


def check_duplicate_application(
    db: Session, candidate_id: uuid.UUID, job_id: uuid.UUID
) -> bool:
    return (
        db.query(Application)
        .filter(
            Application.candidate_id == candidate_id,
            Application.job_id == job_id,
            Application.deleted_at.is_(None),
        )
        .first()
        is not None
    )


def check_duplicate_by_identity(
    db: Session, data: ApplicationCreate, job_id: uuid.UUID, current_candidate_id: uuid.UUID
) -> dict | None:
    """Detect a repeat application from the same person (email or phone)."""
    from app.db.models.application import Application
    from app.db.models.candidate import Candidate

    if check_duplicate_application(db, current_candidate_id, job_id):
        return {"reason": "You have already applied for this job"}

    email = data.email.lower()

    existing = (
        db.query(Candidate)
        .filter(
            Candidate.email == email,
            Candidate.id != current_candidate_id,
            Candidate.deleted_at.is_(None),
        )
        .first()
    )
    if existing:
        dup = (
            db.query(Application)
            .filter(
                Application.candidate_id == existing.id,
                Application.job_id == job_id,
                Application.deleted_at.is_(None),
            )
            .first()
        )
        if dup:
            return {"reason": "You have already applied for this job"}

    phone = _normalize_phone(data.phone)
    if phone:
        candidates = (
            db.query(Candidate)
            .filter(
                Candidate.phone.is_not(None),
                Candidate.id != current_candidate_id,
                Candidate.deleted_at.is_(None),
            )
            .all()
        )
        for cand in candidates:
            if _normalize_phone(cand.phone) == phone:
                dup = (
                    db.query(Application)
                    .filter(
                        Application.candidate_id == cand.id,
                        Application.job_id == job_id,
                        Application.deleted_at.is_(None),
                    )
                    .first()
                )
                if dup:
                    return {
                        "reason": "An application for this job already exists under this phone number"
                    }
    return None


def _previous_rejected_for_job(
    db: Session, candidate_id: uuid.UUID, job_id: uuid.UUID
) -> bool:
    """True when this candidate already applied for the job and was rejected.

    Talent-pool invite re-applications (updated CV) are permitted only in this
    case — the rejected application stays on record and a fresh one is created.
    """
    existing = (
        db.query(Application)
        .filter(
            Application.candidate_id == candidate_id,
            Application.job_id == job_id,
            Application.deleted_at.is_(None),
        )
        .first()
    )
    return existing is not None and existing.status == ApplicationStatus.REJECTED


def create_application(
    db: Session,
    job: Job,
    data: ApplicationCreate,
    file: UploadFile,
    file_contents: bytes,
    *,
    allow_reapply: bool = False,
) -> tuple[Application, str]:
    """Creates candidate + application + CV record + tracking token.

    ``allow_reapply`` (used by the talent-pool invite flow) lets a candidate who
    was previously rejected re-apply to the same job with an updated CV.

    Returns the application and the raw (un-hashed) tracking token.
    """
    if not data.consent:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Application consent is required",
        )

    validate_cv_file(file)
    validate_file_size(file_contents)

    candidate = get_or_create_candidate(db, data)

    duplicate = check_duplicate_by_identity(db, data, job.id, candidate.id)
    if duplicate and not (
        allow_reapply and _previous_rejected_for_job(db, candidate.id, job.id)
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=duplicate["reason"],
        )

    application_id = generate_application_id(db)
    application = Application(
        application_id=application_id,
        candidate_id=candidate.id,
        job_id=job.id,
        expected_salary=data.expected_salary,
        status=ApplicationStatus.APPLIED,
        consent=data.consent,
    )
    db.add(application)
    db.flush()

    file_path, mime_type = file_service.save_cv(file, file_contents)
    cv_doc = CVDocument(
        application_id=application.id,
        file_name=file.filename or "cv",
        file_path=file_path,
        file_hash=hashlib.sha256(file_contents).hexdigest(),
        mime_type=mime_type,
        extraction_status=ExtractionStatus.PENDING,
    )
    db.add(cv_doc)
    db.flush()

    raw_token = generate_secure_token()
    token = ApplicationTrackingToken(
        application_id=application.id,
        token_hash=hash_token(raw_token),
        expires_at=datetime.now(timezone.utc)
        + timedelta(days=settings.TRACKING_TOKEN_EXPIRE_DAYS),
    )
    db.add(token)

    history = ApplicationStatusHistory(
        application_id=application.id,
        from_status=None,
        to_status=ApplicationStatus.APPLIED.value,
        changed_by=None,
        reason="Application submitted",
    )
    db.add(history)

    db.commit()
    db.refresh(application)

    from app.db.models.enums import EmailType
    from app.services.email_service import (
        application_email_body,
        application_email_subject,
        record_email,
    )

    record_email(
        db,
        application_id=application.id,
        email_type=EmailType.APPLICATION,
        recipient=candidate.email,
        subject=application_email_subject(application, EmailType.APPLICATION),
        body=application_email_body(application, EmailType.APPLICATION),
        send=True,
    )

    return application, raw_token


def delete_application(
    db: Session, application: Application, changed_by: uuid.UUID | None
) -> Application:
    """Soft-delete an application (moves it to trash, keeps every record).

    Recovery is possible via :func:`recover_application`; the deletion is
    written to the audit log and to the application status history.
    """
    from app.services import audit_service as audit

    if application.deleted_at is not None:
        return application
    old = application.status
    application.deleted_at = datetime.now(timezone.utc)
    db.add(
        ApplicationStatusHistory(
            application_id=application.id,
            from_status=old.value if old else None,
            to_status="DELETED",
            changed_by=changed_by,
            reason="Application moved to trash",
        )
    )
    audit.log_action(
        db,
        user_id=changed_by,
        action="application.delete",
        entity_type="application",
        entity_id=application.id,
        old_value={"status": old.value if old else None},
        new_value={"status": "DELETED"},
    )
    db.commit()
    db.refresh(application)

    # Cascade: deleting an application also removes the candidate from the
    # talent pool (and with it any other applications the candidate has).
    candidate = application.candidate
    if candidate is not None and candidate.deleted_at is None:
        from app.services.candidate_service import delete_candidate

        delete_candidate(db, candidate, changed_by)
        db.refresh(application)
    return application


def recover_application(
    db: Session, application: Application, changed_by: uuid.UUID | None
) -> Application:
    """Restore a soft-deleted application back into the active list."""
    from app.services import audit_service as audit

    if application.deleted_at is None:
        return application
    previous = application.status
    application.deleted_at = None
    db.add(
        ApplicationStatusHistory(
            application_id=application.id,
            from_status="DELETED",
            to_status=previous.value,
            changed_by=changed_by,
            reason="Application restored from trash",
        )
    )
    audit.log_action(
        db,
        user_id=changed_by,
        action="application.recover",
        entity_type="application",
        entity_id=application.id,
        old_value={"status": "DELETED"},
        new_value={"status": previous.value},
    )
    db.commit()
    db.refresh(application)

    # Reverse cascade: restoring an application brings its candidate back to
    # the talent pool too (together with the candidate's other applications).
    candidate = application.candidate
    if candidate is not None and candidate.deleted_at is not None:
        from app.services.candidate_service import recover_candidate

        recover_candidate(db, candidate, changed_by)
        db.refresh(application)
    return application


def change_status(
    db: Session,
    application: Application,
    new_status: ApplicationStatus,
    changed_by: uuid.UUID | None,
    reason: str | None = None,
    send_email: bool = False,
    email_reason: str | None = None,
    email_context: dict | None = None,
    email_subject: str | None = None,
    email_body: str | None = None,
    force_email: bool = False,
) -> Application:
    from app.db.models.enums import EmailType
    from app.services import audit_service as audit
    from app.services.email_service import (
        application_email_body,
        application_email_subject,
        record_email,
    )

    if application.deleted_at is not None:
        raise HTTPException(
            status_code=400,
            detail="Cannot change status of a deleted application",
        )

    old = application.status
    if old != new_status:
        application.status = new_status
        history = ApplicationStatusHistory(
            application_id=application.id,
            from_status=old.value if old else None,
            to_status=new_status.value,
            changed_by=changed_by,
            reason=reason,
        )
        db.add(history)
        db.flush()

        audit.log_action(
            db,
            user_id=changed_by,
            action="application.status",
            entity_type="application",
            entity_id=application.id,
            old_value={"status": old.value if old else None},
            new_value={"status": new_status.value, "reason": reason},
        )

    if (
        new_status
        in (
            ApplicationStatus.SELECTED,
            ApplicationStatus.REJECTED,
            ApplicationStatus.INTERVIEW_SCHEDULED,
        )
        and application.candidate
        and (old != new_status or force_email)
    ):
        email_type = {
            ApplicationStatus.SELECTED: EmailType.SELECTED,
            ApplicationStatus.REJECTED: EmailType.REJECTED,
            ApplicationStatus.INTERVIEW_SCHEDULED: EmailType.INTERVIEW,
        }[new_status]
        body_kwargs = dict(email_context or {})
        body_kwargs["reason"] = (
            email_reason if email_reason is not None else reason
        )
        body_kwargs["interview"] = (email_context or {}).get("interview")
        record_email(
            db,
            application_id=application.id,
            email_type=email_type,
            recipient=application.candidate.email,
            subject=email_subject
            or application_email_subject(application, email_type),
            body=email_body
            or application_email_body(
                application, email_type, **body_kwargs
            ),
            send=send_email,
        )
        db.commit()

    if (
        new_status
        in (
            ApplicationStatus.SELECTED,
            ApplicationStatus.SHORTLISTED,
        )
        and application.candidate_id is not None
    ):
        from app.services import reply_agent_service

        reply_agent_service.cancel_candidate_pending_interviews(
            db,
            application.candidate_id,
            changed_by=changed_by,
            reason=reason
            or f"Candidate {new_status.value.lower()} — remaining interviews cancelled.",
        )
        db.commit()
    return application


def reject_other_applications_on_selection(
    db: Session,
    selected_application: Application,
    changed_by: uuid.UUID | None,
    reason: str = "Position filled — another candidate has been selected.",
) -> list[Application]:
    """When one candidate is selected for a job, reject all other applicants
    for the same job who are still in the running (not already rejected) and
    send each a rejection email."""
    others = (
        db.query(Application)
        .filter(
            Application.job_id == selected_application.job_id,
            Application.id != selected_application.id,
            Application.status != ApplicationStatus.REJECTED,
            Application.deleted_at.is_(None),
        )
        .all()
    )
    rejected: list[Application] = []
    for application in others:
        change_status(
            db,
            application,
            ApplicationStatus.REJECTED,
            changed_by=changed_by,
            reason=reason,
            send_email=True,
            email_reason=reason,
        )
        rejected.append(application)
    return rejected


def get_application_by_token(db: Session, raw_token: str) -> tuple[Application, str]:
    token_hash = hash_token(raw_token)
    token = (
        db.query(ApplicationTrackingToken)
        .filter(ApplicationTrackingToken.token_hash == token_hash)
        .first()
    )
    if token is None:
        application = (
            db.query(Application)
            .filter(
                Application.application_id == raw_token,
                Application.deleted_at.is_(None),
            )
            .first()
        )
        if application is None:
            raise HTTPException(status_code=404, detail="Tracking link not found")
        return application, application.id.hex

    if token.revoked_at is not None:
        raise HTTPException(status_code=403, detail="Tracking link has been revoked")

    if token.expires_at is not None and token.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=403, detail="Tracking link has expired")

    application = db.get(Application, token.application_id)
    if application is None or application.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Application not found")
    return application, token.application_id.hex