import hashlib
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import func
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


def get_or_create_candidate(
    db: Session, data: ApplicationCreate
) -> Candidate:
    email = data.email.lower()
    candidate = db.query(Candidate).filter(Candidate.email == email).first()
    if candidate:
        return candidate
    candidate = Candidate(
        full_name=data.full_name,
        email=email,
        phone=data.phone,
        address=data.address,
    )
    db.add(candidate)
    db.flush()
    return candidate


def check_duplicate_application(
    db: Session, candidate_id: uuid.UUID, job_id: uuid.UUID
) -> bool:
    return (
        db.query(Application)
        .filter(
            Application.candidate_id == candidate_id,
            Application.job_id == job_id,
        )
        .first()
        is not None
    )


def create_application(
    db: Session,
    job: Job,
    data: ApplicationCreate,
    file: UploadFile,
    file_contents: bytes,
) -> tuple[Application, str]:
    """Creates candidate + application + CV record + tracking token.

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

    if check_duplicate_application(db, candidate.id, job.id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already applied for this job",
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
    return application, raw_token


def change_status(
    db: Session,
    application: Application,
    new_status: ApplicationStatus,
    changed_by: uuid.UUID | None,
    reason: str | None = None,
) -> Application:
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
        db.commit()
    return application


def get_application_by_token(db: Session, raw_token: str) -> tuple[Application, str]:
    token_hash = hash_token(raw_token)
    token = (
        db.query(ApplicationTrackingToken)
        .filter(ApplicationTrackingToken.token_hash == token_hash)
        .first()
    )
    if token is None:
        raise HTTPException(status_code=404, detail="Tracking link not found")

    if token.revoked_at is not None:
        raise HTTPException(status_code=403, detail="Tracking link has been revoked")

    if token.expires_at is not None and token.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=403, detail="Tracking link has expired")

    application = db.get(Application, token.application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found")
    return application, token.application_id.hex