import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.db.models.enums import JobStatus
from app.db.models.job import Job
from app.schemas.job import JobCreate, JobUpdate
from app.services import audit_service as audit
from app.utils.common import jsonify_data


def _get_job_or_404(db: Session, job_id: uuid.UUID) -> Job:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


def create_job(db: Session, data: JobCreate, created_by: uuid.UUID) -> Job:
    job = Job(**data.model_dump(), created_by=created_by)
    db.add(job)
    db.flush()
    audit.log_action(
        db,
        user_id=created_by,
        action="job.create",
        entity_type="job",
        entity_id=job.id,
        new_value=jsonify_data(job),
    )
    db.commit()
    db.refresh(job)
    return job


def update_job(db: Session, job_id: uuid.UUID, data: JobUpdate, changed_by: uuid.UUID | None = None) -> Job:
    job = _get_job_or_404(db, job_id)
    old_value = jsonify_data(job)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(job, key, value)
    db.flush()
    audit.log_action(
        db,
        user_id=changed_by,
        action="job.update",
        entity_type="job",
        entity_id=job.id,
        old_value=old_value,
        new_value=jsonify_data(job),
    )
    db.commit()
    db.refresh(job)
    return job


def publish_job(db: Session, job_id: uuid.UUID, changed_by: uuid.UUID | None = None) -> Job:
    job = _get_job_or_404(db, job_id)
    if job.status == JobStatus.CLOSED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Closed jobs cannot be published",
        )
    job.status = JobStatus.OPEN
    db.flush()
    audit.log_action(
        db,
        user_id=changed_by,
        action="job.publish",
        entity_type="job",
        entity_id=job.id,
        new_value=jsonify_data(job),
    )
    db.commit()
    db.refresh(job)
    return job


def close_job(db: Session, job_id: uuid.UUID, changed_by: uuid.UUID | None = None) -> Job:
    job = _get_job_or_404(db, job_id)
    job.status = JobStatus.CLOSED
    db.flush()
    audit.log_action(
        db,
        user_id=changed_by,
        action="job.close",
        entity_type="job",
        entity_id=job.id,
        new_value=jsonify_data(job),
    )
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