import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.dependencies import get_db, require_hr_or_admin
from app.db.models.user import User
from app.schemas.job import (
    JobAssistantOut,
    JobAssistantRequest,
    JobCreate,
    JobOut,
    JobUpdate,
)
from app.services import invite_service, job_assistant_service, job_service

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.post("/assistant/generate", response_model=JobAssistantOut)
def assistant_generate(
    data: JobAssistantRequest,
    _: User = Depends(require_hr_or_admin),
):
    """Generate a job description + requirements draft from a user prompt.

    The draft is returned for human review and is NOT saved. Save happens via
    the normal create/update job endpoints once the HR user approves it.
    """
    draft = job_assistant_service.generate_job_draft(
        job_title=data.job_title,
        user_note=data.user_input,
    )
    return JobAssistantOut(**draft)


@router.post("", response_model=JobOut, status_code=status.HTTP_201_CREATED)
def create_job(
    data: JobCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin),
):
    job = job_service.create_job(db, data, current_user.id)
    return JobOut.model_validate(job)


@router.get("", response_model=list[JobOut])
def list_jobs(
    db: Session = Depends(get_db),
    _: User = Depends(require_hr_or_admin),
):
    jobs = job_service.list_jobs(db)
    return [JobOut.model_validate(j) for j in jobs]


@router.get("/{job_id}", response_model=JobOut)
def get_job(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_hr_or_admin),
):
    return JobOut.model_validate(job_service.get_job(db, job_id))


@router.patch("/{job_id}", response_model=JobOut)
def update_job(
    job_id: uuid.UUID,
    data: JobUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin),
):
    return JobOut.model_validate(job_service.update_job(db, job_id, data, current_user.id))


@router.post("/{job_id}/publish", response_model=JobOut)
def publish_job(
    job_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin),
):
    job = job_service.publish_job(db, job_id, current_user.id)
    if settings.TALENT_POOL_INVITES_ON_PUBLISH:
        # In the background, invite matching talent-pool candidates (matched by
        # job title) with a one-time apply link in the email.
        background_tasks.add_task(invite_service.send_job_invites, job.id)
    return JobOut.model_validate(job)


@router.post("/{job_id}/close", response_model=JobOut)
def close_job(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin),
):
    return JobOut.model_validate(job_service.close_job(db, job_id, current_user.id))
