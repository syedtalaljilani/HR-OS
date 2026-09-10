import uuid
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.db.models.application import Application
from app.db.models.candidate import Candidate
from app.schemas.candidate import CandidateUpdate
from app.services import application_service


def get_candidate_or_404(
    db: Session, candidate_id: uuid.UUID, include_deleted: bool = False
) -> Candidate:
    candidate = db.get(Candidate, candidate_id)
    if candidate is None or (
        not include_deleted and candidate.deleted_at is not None
    ):
        raise HTTPException(status_code=404, detail="Candidate not found")
    return candidate


def list_candidates(
    db: Session, include_deleted: bool = False
) -> list[Candidate]:
    query = db.query(Candidate).order_by(Candidate.created_at.desc())
    if not include_deleted:
        query = query.filter(Candidate.deleted_at.is_(None))
    return query.all()


def update_candidate(
    db: Session,
    candidate_id: uuid.UUID,
    data: CandidateUpdate,
    include_deleted: bool = False,
) -> Candidate:
    candidate = get_candidate_or_404(db, candidate_id, include_deleted=include_deleted)
    updates = data.model_dump(exclude_unset=True)
    if "email" in updates:
        updates["email"] = updates["email"].lower()
    for key, value in updates.items():
        setattr(candidate, key, value)
    db.commit()
    db.refresh(candidate)
    return candidate


def delete_candidate(
    db: Session, candidate: Candidate, changed_by: uuid.UUID | None
) -> Candidate:
    """Soft-delete a candidate and every one of their applications.

    All rows are kept in the DB (marked with ``deleted_at``) so the whole set
    can be restored later with :func:`recover_candidate`. Every deletion is
    recorded in the audit log.
    """
    from app.services import audit_service as audit

    if candidate.deleted_at is not None:
        return candidate
    candidate.deleted_at = datetime.now(timezone.utc)
    audit.log_action(
        db,
        user_id=changed_by,
        action="candidate.delete",
        entity_type="candidate",
        entity_id=candidate.id,
        old_value={"full_name": candidate.full_name},
        new_value={"status": "DELETED"},
    )
    # Deleting the candidate hides all their applications too. Each app gets
    # its own audit entry + status-history row so the trash is fully auditable.
    apps = (
        db.query(Application)
        .filter(
            Application.candidate_id == candidate.id,
            Application.deleted_at.is_(None),
        )
        .all()
    )
    for app in apps:
        application_service.delete_application(db, app, changed_by)
    db.commit()
    db.refresh(candidate)
    return candidate


def recover_candidate(
    db: Session, candidate: Candidate, changed_by: uuid.UUID | None
) -> Candidate:
    """Restore a soft-deleted candidate and all its deleted applications."""
    from app.services import audit_service as audit

    if candidate.deleted_at is None:
        return candidate
    candidate.deleted_at = None
    # Restore applications that were hidden with the candidate.
    apps = (
        db.query(Application)
        .filter(
            Application.candidate_id == candidate.id,
            Application.deleted_at.is_not(None),
        )
        .all()
    )
    for app in apps:
        application_service.recover_application(db, app, changed_by)
    audit.log_action(
        db,
        user_id=changed_by,
        action="candidate.recover",
        entity_type="candidate",
        entity_id=candidate.id,
        old_value={"status": "DELETED"},
        new_value={"full_name": candidate.full_name},
    )
    db.commit()
    db.refresh(candidate)
    return candidate