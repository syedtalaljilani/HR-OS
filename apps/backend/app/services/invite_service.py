"""Talent-pool job invitations.

When a job is published, matching talent-pool candidates (matched against the
job title) receive an email with a one-time apply link. Clicking it opens the
public apply page pre-filled for that candidate; submitting creates a normal
Application which flows through the usual AI screening + auto email pipeline.
"""
import logging
import re
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import SessionLocal
from app.db.models.application import Application
from app.db.models.candidate import Candidate
from app.db.models.enums import ApplicationStatus, EmailType, JobStatus, TalentPoolStatus
from app.db.models.job import Job
from app.db.models.talent_pool import TalentPool
from app.db.models.talent_pool_invite import TalentPoolInvite
from app.services import settings_service
from app.services.email_service import record_email
from app.utils.tokens import generate_secure_token, hash_token

logger = logging.getLogger("hros.invite")

# Minimum fraction of job-title tokens that must match a candidate's profile
# before we send an invite (e.g. 1 of 3 title tokens).
TITLE_MATCH_MIN = 0.34

_INVITE_STOPWORDS = {
    "a", "an", "the", "of", "and", "or", "for", "in", "on", "at", "to", "with",
    "job", "role", "position", "opening", "vacancy",
}


def _title_tokens(title: str) -> set[str]:
    tokens = set(re.findall(r"[a-z0-9+#.]+", title.lower()))
    return {t for t in tokens if t not in _INVITE_STOPWORDS and len(t) > 1}


def _candidate_title_terms(candidate: Candidate) -> set[str]:
    """Profile signals used to match a candidate against a job title."""
    terms: set[str] = set()
    profile = candidate.profile_data or {}
    for key in ("current_title", "designation", "title", "current_role", "summary"):
        value = profile.get(key)
        if value:
            terms.update(re.findall(r"[a-z0-9+#.]+", str(value).lower()))
    for item in profile.get("experience", []) or []:
        if isinstance(item, dict):
            position = item.get("position") or item.get("role") or item.get("title")
        else:
            position = item
        if position:
            terms.update(re.findall(r"[a-z0-9+#.]+", str(position).lower()))
    for item in profile.get("skills", []) or []:
        terms.update(re.findall(r"[a-z0-9+#.]+", str(item).lower()))
    return terms


def _title_match_score(job_title: str, candidate: Candidate) -> float:
    title = _title_tokens(job_title)
    if not title:
        return 0.0
    terms = _candidate_title_terms(candidate)
    if not terms:
        return 0.0
    return len(title & terms) / len(title)


def _invite_email_parts(
    candidate_name: str,
    job_title: str,
    company_name: str,
    hr_name: str,
    link: str,
) -> tuple[str, str]:
    first = (candidate_name or "there").strip().split()[0]
    valid_days = settings.TALENT_POOL_INVITE_DAYS
    subject = (
        f"{company_name} — {job_title}: you're invited to apply"
        if company_name
        else f"Job opening: {job_title} — you're invited to apply"
    )

    lines = [
        f"Hi {first},",
        "",
    ]
    if company_name:
        lines.append(
            f"We're hiring for the role of {job_title} at {company_name}, and "
            "based on your experience we'd love you to apply."
        )
    else:
        lines.append(
            f"We're hiring for the role of {job_title}, and based on your "
            "experience we'd love you to apply."
        )
    lines += [
        "",
        "Use the link below to update your CV (or confirm your latest one) and "
        "submit your application. Our team reviews every submission personally:",
        "",
        link,
        "",
        f"This invitation link works once and expires in {valid_days} days.",
        "",
    ]
    signoff = ["Best regards,"]
    if hr_name:
        signoff.append(hr_name)
    if company_name:
        signoff.append(company_name)
    else:
        signoff.append("HR Team")
    lines += signoff
    return subject, "\n".join(lines)


def send_job_invites(job_id: uuid.UUID) -> dict:
    """Background task: invite matching talent-pool candidates for a job.

    Runs in its own session (like auto-evaluation) and sends one invite email
    per matching candidate who has not already applied or been invited for the
    job. Never raises — failures are logged per candidate.
    """
    db = SessionLocal()
    try:
        job = db.get(Job, job_id)
        if job is None:
            return {"job_id": str(job_id), "invited": 0, "reason": "job not found"}
        if job.status != JobStatus.OPEN:
            return {"job_id": str(job_id), "invited": 0, "reason": "job not open"}

        applied_ids = {
            row[0]
            for row in db.query(Application.candidate_id)
            .filter(
                Application.job_id == job.id,
                Application.deleted_at.is_(None),
            )
            .all()
        }
        invited_ids = {
            row[0]
            for row in db.query(TalentPoolInvite.candidate_id)
            .filter(TalentPoolInvite.job_id == job.id)
            .all()
        }

        entries = (
            db.query(TalentPool)
            .filter(
                TalentPool.status.in_(
                    [
                        TalentPoolStatus.ACTIVE,
                        TalentPoolStatus.CONTACTED,
                        TalentPoolStatus.INTERESTED,
                    ]
                ),
                TalentPool.consent.is_(True),
            )
            .all()
        )

        company_name, hr_name, _ = settings_service.org_identity(db)
        invited = 0
        now = datetime.now(timezone.utc)
        for entry in entries:
            candidate = entry.candidate
            if candidate is None or not candidate.email:
                continue
            if candidate.id in applied_ids or candidate.id in invited_ids:
                continue
            if _title_match_score(job.title, candidate) < TITLE_MATCH_MIN:
                continue
            try:
                raw_token = generate_secure_token()
                invite = TalentPoolInvite(
                    token_hash=hash_token(raw_token),
                    candidate_id=candidate.id,
                    job_id=job.id,
                    expires_at=now + timedelta(days=settings.TALENT_POOL_INVITE_DAYS),
                )
                db.add(invite)
                db.flush()

                link = f"{settings.PUBLIC_BASE_URL}/apply/{raw_token}"
                subject, body = _invite_email_parts(
                    candidate.full_name,
                    job.title,
                    company_name,
                    hr_name,
                    link,
                )
                record_email(
                    db,
                    application_id=None,
                    email_type=EmailType.TALENT_POOL,
                    recipient=candidate.email,
                    subject=subject,
                    body=body,
                    send=True,
                )
                if entry.status == TalentPoolStatus.ACTIVE:
                    entry.status = TalentPoolStatus.CONTACTED
                invited += 1
            except Exception:
                db.rollback()
                logger.exception(
                    "Failed to invite candidate %s for job %s",
                    candidate.id,
                    job.id,
                )
        db.commit()
        logger.info(
            "Job %s published: invited %d talent-pool candidate(s)",
            job.id,
            invited,
        )
        return {"job_id": str(job.id), "invited": invited}
    finally:
        db.close()


def resolve_invite(db: Session, raw_token: str) -> tuple[TalentPoolInvite, Candidate, Job]:
    """Resolve + validate a raw invite token into (invite, candidate, job)."""
    invite = (
        db.query(TalentPoolInvite)
        .filter(TalentPoolInvite.token_hash == hash_token(raw_token))
        .first()
    )
    if invite is None:
        raise HTTPException(
            status_code=404,
            detail="This invitation link is not valid",
        )
    if invite.used_at is not None:
        raise HTTPException(
            status_code=410,
            detail="This invitation has already been used",
        )
    if invite.expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=410,
            detail="This invitation has expired",
        )

    candidate = db.get(Candidate, invite.candidate_id)
    job = db.get(Job, invite.job_id)
    if candidate is None or job is None:
        raise HTTPException(
            status_code=404,
            detail="This invitation is no longer available",
        )
    if job.status != JobStatus.OPEN:
        raise HTTPException(
            status_code=400,
            detail="This job opening is no longer accepting applications",
        )
    return invite, candidate, job


def mark_invite_used(db: Session, invite: TalentPoolInvite) -> None:
    invite.used_at = datetime.now(timezone.utc)
    db.flush()