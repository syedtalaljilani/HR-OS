import re
import uuid
from decimal import Decimal, InvalidOperation

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.dependencies import get_db
from app.schemas.application import (
    ApplicationCreate,
    ApplicationHistoryOut,
    ApplicationTrackingResponse,
)
from app.schemas.interview import RescheduleSubmit, RescheduleView
from app.schemas.invite import InvitePublicOut
from app.schemas.job import JobOut
from app.services import (
    application_service,
    extraction_service,
    interview_service,
    invite_service,
    job_service,
    settings_service,
)
from app.utils.validators import validate_cv_file, validate_file_size

router = APIRouter(prefix="/public", tags=["Public"])


def _parse_salary(value: str | None) -> Decimal | None:
    """Tolerantly parse an expected-salary string (e.g. "50,000", "PKR 30k")."""
    if not value or not value.strip():
        return None
    cleaned = re.sub(r"[^\d.]", "", value.replace(",", ""))
    if not cleaned:
        return None
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


def _build_application_data(
    full_name: str,
    email: str,
    phone: str | None,
    address: str | None,
    expected_salary: str | None,
    consent: str,
    skills: str | None,
    education: str | None,
    experience: str | None,
    profile_data: str | None,
) -> ApplicationCreate:
    return ApplicationCreate(
        full_name=full_name,
        email=email,
        phone=phone,
        address=address,
        expected_salary=_parse_salary(expected_salary),
        consent=consent.strip().lower() in ("true", "1", "yes", "on"),
        skills=skills,
        education=education,
        experience=experience,
        profile_data=profile_data,
    )


async def _submit_application(
    db: Session,
    job: "Job",
    file: UploadFile,
    data: ApplicationCreate,
    *,
    allow_reapply: bool = False,
) -> dict:
    """Shared apply submission used by the public and invite flows."""
    contents = await file.read()
    application, raw_token = application_service.create_application(
        db,
        job,
        data,
        file,
        contents,
        allow_reapply=allow_reapply,
    )

    if settings.AUTO_EVALUATE_ON_APPLY:
        from app.services import screening_queue_service

        screening_queue_service.enqueue(
            db,
            application,
            source=screening_queue_service.SOURCE_AUTO,
            action=screening_queue_service.ACTION_EVALUATE,
        )

    return {
        "applicationId": application.application_id,
        "status": application.status.value,
        "customerId": application.id,
        "trackingUrl": f"/application/{raw_token}",
    }


@router.post("/cv/extract")
async def extract_cv(
    file: UploadFile = File(...),
):
    """Extract the full text layer from a CV and return a structured candidate profile.

    Used by the public apply form to pre-fill the application fields. No OCR —
    reads the native PDF/DOCX/TXT text layer. The profile is NOT persisted here
    — the user reviews/edits it before submit.
    """
    validate_cv_file(file)
    contents = await file.read()
    validate_file_size(contents)

    result = extraction_service.extract_profile_from_cv(
        contents,
        file.filename or "cv.pdf",
    )
    return {"profile": result["profile"], "text": result["text"]}


@router.get("/jobs", response_model=list[JobOut])
def list_open_jobs(db: Session = Depends(get_db)):
    jobs = job_service.list_open_jobs(db)
    return [JobOut.model_validate(j) for j in jobs]


@router.get("/jobs/{job_id}", response_model=JobOut)
def get_open_job(job_id: uuid.UUID, db: Session = Depends(get_db)):
    return JobOut.model_validate(job_service.get_open_job(db, job_id))


@router.post(
    "/jobs/{job_id}/apply",
    status_code=status.HTTP_201_CREATED,
)
async def apply_for_job(
    job_id: uuid.UUID,
    file: UploadFile = File(...),
    full_name: str = Form(...),
    email: str = Form(...),
    phone: str | None = Form(default=None),
    address: str | None = Form(default=None),
    expected_salary: str | None = Form(default=None),
    consent: str = Form(default="true"),
    skills: str | None = Form(default=None),
    education: str | None = Form(default=None),
    experience: str | None = Form(default=None),
    profile_data: str | None = Form(default=None),
    db: Session = Depends(get_db),
):
    job = job_service.get_open_job(db, job_id)

    data = _build_application_data(
        full_name=full_name,
        email=email,
        phone=phone,
        address=address,
        expected_salary=expected_salary,
        consent=consent,
        skills=skills,
        education=education,
        experience=experience,
        profile_data=profile_data,
    )

    result = await _submit_application(db, job, file, data)
    return result


@router.get("/invitations/{raw_token}", response_model=InvitePublicOut)
def get_invitation(raw_token: str, db: Session = Depends(get_db)):
    """Resolve a talent-pool invitation link (public landing page data)."""
    _, candidate, job = invite_service.resolve_invite(db, raw_token)
    company_name, _, _ = settings_service.org_identity(db)
    return InvitePublicOut(
        job_id=job.id,
        job_title=job.title,
        job_location=job.location,
        candidate_name=candidate.full_name,
        candidate_email=candidate.email,
        company_name=company_name,
    )


@router.post(
    "/invitations/{raw_token}/apply",
    status_code=status.HTTP_201_CREATED,
)
async def apply_via_invitation(
    raw_token: str,
    file: UploadFile = File(...),
    full_name: str = Form(...),
    email: str = Form(...),
    phone: str | None = Form(default=None),
    address: str | None = Form(default=None),
    expected_salary: str | None = Form(default=None),
    consent: str = Form(default="true"),
    skills: str | None = Form(default=None),
    education: str | None = Form(default=None),
    experience: str | None = Form(default=None),
    profile_data: str | None = Form(default=None),
    db: Session = Depends(get_db),
):
    """Submit (possibly updated) CV via a talent-pool invitation link.

    Runs the exact same flow as a normal application: creates the Application,
    marks the invite used, then triggers the usual AI screening + auto
    reject/edit email pipeline.
    """
    invite, _, job = invite_service.resolve_invite(db, raw_token)

    data = _build_application_data(
        full_name=full_name,
        email=email,
        phone=phone,
        address=address,
        expected_salary=expected_salary,
        consent=consent,
        skills=skills,
        education=education,
        experience=experience,
        profile_data=profile_data,
    )

    result = await _submit_application(
        db,
        job,
        file,
        data,
        allow_reapply=True,
    )
    invite_service.mark_invite_used(db, invite)
    db.commit()
    return result


@router.get("/applications/{raw_token}", response_model=ApplicationTrackingResponse)
def track_application(raw_token: str, db: Session = Depends(get_db)):
    application, _ = application_service.get_application_by_token(db, raw_token)

    history = application.status_history or []
    history_out = [
        ApplicationHistoryOut.model_validate(h) for h in sorted(
            history, key=lambda h: h.created_at
        )
    ]

    return ApplicationTrackingResponse(
        application_id=application.application_id,
        status=application.status,
        candidate_name=application.candidate.full_name,
        job_title=application.job.title,
        created_at=application.created_at,
        updated_at=application.updated_at,
        status_history=history_out,
    )


def _resolve_reschedule(db: Session, raw_token: str) -> "Interview":
    """Find the interview that owns this reschedule token."""
    from app.db.models.interview import Interview

    interview = (
        db.query(Interview)
        .filter(Interview.reschedule_token == raw_token)
        .first()
    )
    if interview is None:
        raise HTTPException(
            status_code=404,
            detail="This reschedule link is not valid",
        )
    application = interview.application
    if application is None or application.deleted_at is not None:
        raise HTTPException(
            status_code=404,
            detail="This reschedule link is not valid",
        )
    return interview


def _to_reschedule_view(db: Session, interview: "Interview") -> RescheduleView:
    from app.db.models.enums import (
        InterviewRequestStatus,
        InterviewRequestType,
    )
    from app.db.models.interview import InterviewRequest

    application = interview.application
    pending_remote = (
        db.query(InterviewRequest.id)
        .filter(
            InterviewRequest.application_id == application.id,
            InterviewRequest.type == InterviewRequestType.REMOTE,
            InterviewRequest.status == InterviewRequestStatus.PENDING,
        )
        .first()
        is not None
    )
    return RescheduleView(
        application_id=application.id,
        candidate_name=application.candidate.full_name,
        job_title=application.job.title if application.job else "the position",
        interview_id=interview.id,
        type=interview.type,
        scheduled_at=interview.scheduled_at,
        location=interview.location,
        notes=interview.notes,
        available_slots=interview_service.interview_slots(interview),
        pending_remote=pending_remote,
        already_rescheduled=interview.status.value
        != "SCHEDULED",
    )


@router.get("/reschedule/{raw_token}", response_model=RescheduleView)
def get_reschedule(raw_token: str, db: Session = Depends(get_db)):
    """Public landing page for the interview reschedule link."""
    interview = _resolve_reschedule(db, raw_token)
    return _to_reschedule_view(db, interview)


@router.post("/reschedule/{raw_token}", response_model=RescheduleView)
def submit_reschedule(
    raw_token: str,
    data: RescheduleSubmit,
    db: Session = Depends(get_db),
):
    """Candidate picks a new slot (previous interview is cancelled) and/or
    requests a remote interview, which HR reviews from the dashboard."""
    from app.db.models.enums import InterviewStatus

    interview = _resolve_reschedule(db, raw_token)
    if interview.status != InterviewStatus.SCHEDULED:
        raise HTTPException(
            status_code=409,
            detail="This interview has already been handled.",
        )

    has_slot = data.selected_slot is not None
    has_remote = bool((data.remote_reason or "").strip())
    if not has_slot and not has_remote:
        raise HTTPException(
            status_code=400,
            detail="Select a slot or request a remote interview.",
        )

    handled: "Interview | None" = None
    if has_slot:
        selected = interview_service.as_utc(data.selected_slot)
        slots = interview_service.interview_slots(interview)
        if selected not in slots:
            raise HTTPException(
                status_code=400,
                detail="The selected slot is not available.",
            )
        if selected != interview_service.as_utc(interview.scheduled_at):
            handled = interview_service.candidate_reschedule(
                db, interview, selected
            )

    if has_remote:
        interview_service.upsert_remote_request(
            db, interview, data.remote_reason
        )

    target = handled or interview
    return _to_reschedule_view(db, target)