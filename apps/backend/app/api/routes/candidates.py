import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, require_hr_or_admin
from app.db.models.user import User
from app.schemas.candidate import CandidateOut, CandidateUpdate
from app.services import candidate_service

router = APIRouter(prefix="/candidates", tags=["Candidates"])


@router.get("", response_model=list[CandidateOut])
def list_candidates(
    db: Session = Depends(get_db),
    _: User = Depends(require_hr_or_admin),
):
    candidates = candidate_service.list_candidates(db)
    return [CandidateOut.model_validate(c) for c in candidates]


@router.get("/{candidate_id}", response_model=CandidateOut)
def get_candidate(
    candidate_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_hr_or_admin),
):
    candidate = candidate_service.get_candidate_or_404(db, candidate_id)
    return CandidateOut.model_validate(candidate)


@router.patch("/{candidate_id}", response_model=CandidateOut)
def update_candidate(
    candidate_id: uuid.UUID,
    data: CandidateUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_hr_or_admin),
):
    candidate = candidate_service.update_candidate(db, candidate_id, data)
    return CandidateOut.model_validate(candidate)