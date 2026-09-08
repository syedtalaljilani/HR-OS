import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, require_hr_or_admin
from app.db.models.enums import TalentPoolStatus
from app.db.models.user import User
from app.schemas.talent_pool import (
    TalentPoolAdd,
    TalentPoolCandidateOut,
    TalentPoolMatchRequest,
    TalentPoolMatchResponse,
    TalentPoolOut,
    TalentPoolStatusUpdate,
)
from app.services import talent_pool_service

router = APIRouter(prefix="/talent-pool", tags=["Talent Pool"])


def _candidate_out(entry) -> TalentPoolCandidateOut:
    base = TalentPoolOut.model_validate(entry).model_dump()
    candidate = entry.candidate
    return TalentPoolCandidateOut(
        **base,
        candidate_name=candidate.full_name if candidate else None,
        candidate_email=candidate.email if candidate else None,
    )


@router.post("/match", response_model=TalentPoolMatchResponse)
def match(
    data: TalentPoolMatchRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_hr_or_admin),
):
    matches = talent_pool_service.match_candidates(db, data)
    return TalentPoolMatchResponse(matches=matches)


@router.post("/{candidate_id}", response_model=TalentPoolOut, status_code=status.HTTP_201_CREATED)
def add_to_pool(
    candidate_id: uuid.UUID,
    data: TalentPoolAdd,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin),
):
    entry = talent_pool_service.add_to_pool(
        db, candidate_id, data.source_application_id, data.consent, current_user.id
    )
    return TalentPoolOut.model_validate(entry)


@router.get("", response_model=list[TalentPoolCandidateOut])
def list_pool(
    db: Session = Depends(get_db),
    _: User = Depends(require_hr_or_admin),
    status_filter: TalentPoolStatus | None = Query(default=None, alias="status"),
):
    entries = talent_pool_service.list_pool(db, status_filter)
    return [_candidate_out(e) for e in entries]


@router.post("/{pool_id}/contact", response_model=TalentPoolOut)
def contact(
    pool_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_hr_or_admin),
):
    entry = talent_pool_service.update_status(
        db, pool_id, TalentPoolStatus.CONTACTED
    )
    return TalentPoolOut.model_validate(entry)


@router.patch("/{pool_id}/status", response_model=TalentPoolOut)
def update_status(
    pool_id: uuid.UUID,
    data: TalentPoolStatusUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_hr_or_admin),
):
    entry = talent_pool_service.update_status(db, pool_id, data.status)
    return TalentPoolOut.model_validate(entry)