import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.schemas.application import (
    ApplicationCreate,
    ApplicationHistoryOut,
    ApplicationTrackingResponse,
)
from app.schemas.job import JobOut
from app.services import application_service, extraction_service, job_service
from app.utils.validators import validate_cv_file, validate_file_size
from app.core.config import settings

router = APIRouter(prefix="/public", tags=["Public"])


@router.post("/cv/extract")
async def extract_cv(
    file: UploadFile = File(...),
):
    """OCR a CV with DeepSeek-OCR and return a structured candidate profile.

    Used by the public apply form to pre-fill the application fields. The
    profile is NOT persisted here — the user reviews/edits it before submit.
    """
    validate_cv_file(file)
    contents = await file.read()
    validate_file_size(contents)

    profile = extraction_service.extract_profile_with_ocr(
        contents,
        file.filename or "cv.pdf",
        dpi=settings.OCR_PAGE_DPI,
    )
    return {"profile": profile}


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
    db: Session = Depends(get_db),
):
    job = job_service.get_open_job(db, job_id)

    data = ApplicationCreate(
        full_name=full_name,
        email=email,
        phone=phone,
        address=address,
        expected_salary=Decimal(expected_salary) if expected_salary else None,
        consent=consent.strip().lower() in ("true", "1", "yes", "on"),
        skills=skills,
        education=education,
        experience=experience,
    )

    contents = await file.read()
    application, raw_token = application_service.create_application(
        db, job, data, file, contents
    )

    return {
        "applicationId": application.application_id,
        "status": application.status.value,
        "customerId": application.id,
        "trackingUrl": f"/application/{raw_token}",
    }


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