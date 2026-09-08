import uuid

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.db.models.candidate import Candidate
from app.schemas.candidate import CandidateUpdate


def get_candidate_or_404(db: Session, candidate_id: uuid.UUID) -> Candidate:
    candidate = db.get(Candidate, candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return candidate


def list_candidates(db: Session) -> list[Candidate]:
    return db.query(Candidate).order_by(Candidate.created_at.desc()).all()


def update_candidate(
    db: Session, candidate_id: uuid.UUID, data: CandidateUpdate
) -> Candidate:
    candidate = get_candidate_or_404(db, candidate_id)
    updates = data.model_dump(exclude_unset=True)
    if "email" in updates:
        updates["email"] = updates["email"].lower()
    for key, value in updates.items():
        setattr(candidate, key, value)
    db.commit()
    db.refresh(candidate)
    return candidate