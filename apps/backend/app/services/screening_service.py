import re
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.db.models.application import Application, ScreeningResult
from app.db.models.candidate import Candidate
from app.db.models.enums import (
    ApplicationStatus,
    ExtractionStatus,
    HRDecision,
    Recommendation,
)
from app.db.models.job import Job
from app.core.config import settings
from app.services import ai_client, extraction_service

STOPWORDS = {
    "a", "an", "the", "of", "and", "or", "for", "in", "on", "with", "to", "at",
    "by", "years", "year", "experience", "experience.", "using", "knowledge",
}


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9+#.]+", text.lower()))


def _match_requirement_deterministic(requirement: str, cv_text: str) -> dict:
    req_tokens = _tokenize(requirement) - STOPWORDS
    cv_tokens = _tokenize(cv_text)
    if not req_tokens:
        return {"requirement": requirement, "status": "UNCLEAR", "evidence": None}

    hits = req_tokens & cv_tokens
    ratio = len(hits) / len(req_tokens)

    if ratio >= 1.0:
        match_status = "MATCH"
    elif ratio >= 0.5:
        match_status = "PARTIAL"
    else:
        match_status = "MISSING"

    evidence = None
    for sentence in re.split(r"[.\n]", cv_text):
        lower = sentence.lower()
        if any(t in lower for t in hits):
            evidence = sentence.strip()
            if len(evidence) > 20:
                break
    if evidence and len(evidence) > 300:
        evidence = evidence[:300]

    return {
        "requirement": requirement,
        "status": match_status,
        "evidence": evidence,
    }


def process_application(db: Session, application: Application) -> dict:
    """Extract CV text, build candidate profile, validate, check duplicates."""
    application.candidate.embedding  # touch relationship
    cv = application.cv_documents[0] if application.cv_documents else None
    if cv is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No CV document found for this application",
        )

    if cv.extraction_status == ExtractionStatus.FAILED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CV extraction previously failed",
        )

    text = extraction_service.extract_text_from_cv(cv)
    cv.extracted_text = text
    cv.extraction_status = ExtractionStatus.COMPLETED

    profile = extraction_service.extract_candidate_profile(text)
    validation = extraction_service.validate_cv(text, profile)

    candidate: Candidate = application.candidate
    existing_profile = candidate.profile_data or {}
    for key, value in profile.items():
        if value is not None and not existing_profile.get(key):
            existing_profile[key] = value
    candidate.profile_data = existing_profile
    candidate.full_name = profile.get("name") or candidate.full_name

    embedding_source = extraction_service.build_embedding_source(profile)
    if extraction_service.should_embed_candidate(profile):
        embedding = ai_client.embed_text(embedding_source)
        if embedding is not None:
            candidate.embedding = embedding

    duplicates = extraction_service.detect_duplicates(db, candidate, cv)

    _transition_status(
        db,
        application,
        ApplicationStatus.PROCESSING,
        reason="CV processing completed" if validation["valid"] else "CV processing completed with issues",
    )

    db.commit()

    return {
        "application_id": application.application_id,
        "extraction_status": cv.extraction_status.value,
        "text_length": len(text),
        "profile": profile,
        "validation": validation,
        "duplicates": duplicates,
        "candidate_embedded": candidate.embedding is not None,
        "status": application.status.value,
    }


def _screen_requirements_ai(requirements: list[str], cv_text: str, job_title: str) -> list[dict] | None:
    try:
        result = ai_client.chat_json(
            [
                {
                    "role": "system",
                    "content": (
                        "You compare a candidate CV against job requirements. "
                        "Return ONLY JSON: a list with one object per requirement "
                        "with keys: requirement, status (MATCH/PARTIAL/MISSING/UNCLEAR), evidence (string or null)."
                    ),
                },
                {
                    "role": "user",
                    "content": "Requirements:\n"
                    + "\n".join(f"- {r}" for r in requirements)
                    + f"\n\nJob title: {job_title}\n\nCV:\n{cv_text[:6000]}",
                },
            ],
            model=settings.OLLAMA_EVALUATION_MODEL,
        )
        items = result.get("results") or result.get("matches") or result.get("requirements")
        if isinstance(items, list) and items and "status" in items[0]:
            return items
    except ai_client.AIUnavailable:
        pass
    except (TimeoutError, OSError):
        pass
    return None


def screen_application(db: Session, application: Application) -> ScreeningResult:
    cv = application.cv_documents[0] if application.cv_documents else None
    job: Job = application.job
    cv_text = cv.extracted_text if cv else ""

    requirements = extraction_service.update_job_requirements(job)
    if not requirements:
        requirements = ["Relevant skills and qualifications for " + (job.title or "the role")]

    ai_items = _screen_requirements_ai(requirements, cv_text, job.title or "")
    if ai_items is not None:
        matched = [str(i.get("status", "")).upper() for i in ai_items]
        req_list = [str(i.get("requirement", "")) for i in ai_items]
        evidence = ai_items
    else:
        matched = []
        evidence = []
        req_list = []
        for requirement in requirements:
            result = _match_requirement_deterministic(requirement, cv_text)
            matched.append(result["status"])
            evidence.append(result)
            req_list.append(result["requirement"])

    score_value = 0
    for m in matched:
        if m == "MATCH":
            score_value += 100
        elif m == "PARTIAL":
            score_value += 50
    total_score = int(score_value / len(matched)) if matched else 0

    if total_score >= 70:
        recommendation = Recommendation.MATCH
    elif total_score >= 40:
        recommendation = Recommendation.PARTIAL
    elif total_score > 0:
        recommendation = Recommendation.MISSING
    else:
        recommendation = Recommendation.UNCLEAR

    missing = [e for e in evidence if e.get("status") in ("MISSING",)]
    uncertain = [e for e in evidence if e.get("status") in ("UNCLEAR", "PARTIAL")]

    screening = ScreeningResult(
        application_id=application.id,
        recommendation=recommendation,
        score=Decimal(total_score),
        evidence={"items": evidence},
        missing_requirements={"items": missing},
        uncertainty={"items": uncertain},
        model=(
            "ollama/" + DEFAULT_MODEL_REF
            if ai_items is not None
            else "deterministic-fallback"
        ),
        hr_decision=HRDecision.PENDING,
    )
    db.add(screening)

    _transition_status(
        db,
        application,
        ApplicationStatus.HR_REVIEW,
        reason=f"AI screening completed: {recommendation.value} ({total_score}/100)",
    )

    db.commit()
    db.refresh(screening)
    application.screening_results.append(screening)
    return screening


DEFAULT_MODEL_REF = "qwen2.5:7b"


def _transition_status(
    db: Session,
    application: Application,
    new_status: ApplicationStatus,
    reason: str | None = None,
) -> None:
    from app.db.models.application import ApplicationStatusHistory

    old = application.status
    if old == new_status:
        return
    application.status = new_status
    instruction = ApplicationStatusHistory(
        application_id=application.id,
        from_status=old.value if old else None,
        to_status=new_status.value,
        changed_by=None,
        reason=reason,
    )
    db.add(instruction)