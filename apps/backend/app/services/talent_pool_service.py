import re
import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.candidate import Candidate
from app.db.models.enums import TalentPoolStatus
from app.db.models.job import Job
from app.db.models.talent_pool import TalentPool
from app.schemas.talent_pool import TalentPoolMatchRequest
from app.services import ai_client


def _get_candidate_or_404(db: Session, candidate_id: uuid.UUID) -> Candidate:
    candidate = db.get(Candidate, candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return candidate


def add_to_pool(
    db: Session,
    candidate_id: uuid.UUID,
    source_application_id: uuid.UUID | None,
    consent: bool,
    added_by: uuid.UUID | None,
) -> TalentPool:
    candidate = _get_candidate_or_404(db, candidate_id)
    existing = (
        db.query(TalentPool)
        .filter(TalentPool.candidate_id == candidate.id)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Candidate is already in the talent pool",
        )
    if not consent:
        raise HTTPException(
            status_code=400,
            detail="Talent pool consent is required",
        )
    entry = TalentPool(
        candidate_id=candidate.id,
        source_application_id=source_application_id,
        status=TalentPoolStatus.ACTIVE,
        consent=consent,
        added_by=added_by,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def list_pool(db: Session, status: TalentPoolStatus | None = None) -> list[TalentPool]:
    query = db.query(TalentPool).order_by(TalentPool.created_at.desc())
    if status is not None:
        query = query.filter(TalentPool.status == status)
    return query.all()


def update_status(
    db: Session, pool_id: uuid.UUID, new_status: TalentPoolStatus
) -> TalentPool:
    entry = db.get(TalentPool, pool_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Talent pool entry not found")
    entry.status = new_status
    db.commit()
    db.refresh(entry)
    return entry


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _candidate_terms(candidate: Candidate) -> set[str]:
    terms: set[str] = set()
    profile = candidate.profile_data or {}
    for key in ("skills", "experience"):
        for item in profile.get(key, []) or []:
            terms.update(re.findall(r"[a-z0-9+#.]+", str(item).lower()))
    return terms


def _job_terms(job: Job) -> set[str]:
    terms: set[str] = set()
    requirements = job.requirements or {}
    if isinstance(requirements, dict):
        for key in ("skills", "experience", "education", "requirements"):
            value = requirements.get(key)
            if isinstance(value, list):
                for item in value:
                    terms.update(re.findall(r"[a-z0-9+#.]+", str(item).lower()))
            elif isinstance(value, str):
                terms.update(re.findall(r"[a-z0-9+#.]+", value.lower()))
    return terms


def match_candidates(
    db: Session, request: TalentPoolMatchRequest
) -> list[dict]:
    job = db.get(Job, request.job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    entries = (
        db.query(TalentPool)
        .filter(TalentPool.status.notin_(
            [TalentPoolStatus.EXPIRED.value, TalentPoolStatus.REMOVED.value]
        ))
        .all()
    )

    job_terms = _job_terms(job)
    job_text_parts = list(job_terms)
    job_embedding = ai_client.embed_text(" ".join(job_text_parts))

    results = []
    for entry in entries:
        candidate = entry.candidate
        similarity = 0.0

        if job_embedding is not None and candidate.embedding is not None:
            query = select(
                (1 - candidate.embedding.cosine_distance(job_embedding)).label("sim")
            ).where(Candidate.id == candidate.id)
            distance = db.execute(query).scalar()
            if distance is not None:
                similarity = float(distance)

        if similarity == 0.0:
            terms = _candidate_terms(candidate)
            if terms and job_terms:
                similarity = _jaccard(terms, job_terms)

        results.append(
            {
                "pool_id": entry.id,
                "candidate_id": candidate.id,
                "candidate_name": candidate.full_name,
                "similarity": round(similarity, 3),
            }
        )

    results.sort(key=lambda r: r["similarity"], reverse=True)
    return results[: request.limit]