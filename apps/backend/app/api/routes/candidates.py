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
    include_deleted: bool = False,
):
    candidates = candidate_service.list_candidates(db, include_deleted=include_deleted)
    return [CandidateOut.model_validate(c) for c in candidates]


@router.get("/{candidate_id}", response_model=CandidateOut)
def get_candidate(
    candidate_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_hr_or_admin),
    include_deleted: bool = False,
):
    candidate = candidate_service.get_candidate_or_404(
        db, candidate_id, include_deleted=include_deleted
    )
    return CandidateOut.model_validate(candidate)


@router.patch("/{candidate_id}", response_model=CandidateOut)
def update_candidate(
    candidate_id: uuid.UUID,
    data: CandidateUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_hr_or_admin),
    include_deleted: bool = False,
):
    candidate = candidate_service.update_candidate(
        db, candidate_id, data, include_deleted=include_deleted
    )
    return CandidateOut.model_validate(candidate)


@router.delete("/{candidate_id}", response_model=CandidateOut)
def delete_candidate(
    candidate_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin),
):
    """Soft-delete a candidate and all their applications (recoverable)."""
    candidate = candidate_service.get_candidate_or_404(
        db, candidate_id, include_deleted=True
    )
    return CandidateOut.model_validate(
        candidate_service.delete_candidate(db, candidate, current_user.id)
    )


@router.post("/{candidate_id}/recover", response_model=CandidateOut)
def recover_candidate(
    candidate_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin),
):
    """Restore a deleted candidate and all their deleted applications."""
    candidate = candidate_service.get_candidate_or_404(
        db, candidate_id, include_deleted=True
    )
    return CandidateOut.model_validate(
        candidate_service.recover_candidate(db, candidate, current_user.id)
    )