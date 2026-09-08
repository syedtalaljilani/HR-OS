import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.db.models.enums import JobStatus
from app.db.models.job import Job
from app.schemas.job import JobCreate, JobUpdate


def _get_job_or_404(db: Session, job_id: uuid.UUID) -> Job:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


def create_job(db: Session, data: JobCreate, created_by: uuid.UUID) -> Job:
    job = Job(**data.model_dump(), created_by=created_by)
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def update_job(db: Session, job_id: uuid.UUID, data: JobUpdate) -> Job:
    job = _get_job_or_404(db, job_id)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(job, key, value)
    db.commit()
    db.refresh(job)
    return job


def publish_job(db: Session, job_id: uuid.UUID) -> Job:
    job = _get_job_or_404(db, job_id)
    if job.status == JobStatus.CLOSED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Closed jobs cannot be published",
        )
    job.status = JobStatus.OPEN
    db.commit()
    db.refresh(job)
    return job


def close_job(db: Session, job_id: uuid.UUID) -> Job:
    job = _get_job_or_404(db, job_id)
    job.status = JobStatus.CLOSED
    db.commit()
    db.refresh(job)
    return job


def list_jobs(db: Session) -> list[Job]:
    return db.query(Job).order_by(Job.created_at.desc()).all()


def get_job(db: Session, job_id: uuid.UUID) -> Job:
    return _get_job_or_404(db, job_id)


def list_open_jobs(db: Session) -> list[Job]:
    return (
        db.query(Job)
        .filter(Job.status == JobStatus.OPEN)
        .order_by(Job.created_at.desc())
        .all()
    )


def get_open_job(db: Session, job_id: uuid.UUID) -> Job:
    job = _get_job_or_404(db, job_id)
    if job.status != JobStatus.OPEN:
        raise HTTPException(status_code=404, detail="Job not found")
    return job