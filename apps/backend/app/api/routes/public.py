import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.schemas.job import JobOut
from app.services import job_service

router = APIRouter(prefix="/public", tags=["Public"])


@router.get("/jobs", response_model=list[JobOut])
def list_open_jobs(db: Session = Depends(get_db)):
    jobs = job_service.list_open_jobs(db)
    return [JobOut.model_validate(j) for j in jobs]


@router.get("/jobs/{job_id}", response_model=JobOut)
def get_open_job(job_id: uuid.UUID, db: Session = Depends(get_db)):
    return JobOut.model_validate(job_service.get_open_job(db, job_id))