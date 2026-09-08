"""Adapter that runs the LangGraph screening workflow against a DB application.

The `ai` package lives at the repository root. The FastAPI backend runs from
`apps/backend`, so we make the repo root importable here.
"""
import sys
from decimal import Decimal
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[4]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from sqlalchemy.orm import Session

from ai.graphs.screening import graph
from ai.schemas import ScreeningState

from app.core.config import settings
from app.db.models.application import Application, ScreeningResult
from app.db.models.enums import (
    ApplicationStatus,
    ExtractionStatus,
    HRDecision,
    Recommendation,
)
from app.services import extraction_service


def _build_job_description(application: Application) -> str:
    """Turn job description + structured requirements into one prompt input."""
    job = application.job
    parts = [job.title or ""]
    if job.description:
        parts.append(job.description)
    reqs = extraction_service.update_job_requirements(job)
    if reqs:
        parts.append("Requirements:\n" + "\n".join(f"- {r}" for r in reqs))
    return "\n\n".join(p for p in parts if p)


def screen_application(db: Session, application: Application) -> ScreeningResult:
    """Run the LangGraph workflow and persist the result as a ScreeningResult."""
    cv = application.cv_documents[0] if application.cv_documents else None
    if cv is None:
        raise ValueError("No CV document found for this application")
    if cv.extraction_status == ExtractionStatus.FAILED:
        raise ValueError("CV extraction previously failed")

    cv_text = cv.extracted_text
    if not cv_text:
        cv_text = extraction_service.extract_text_from_cv(cv)
        cv.extracted_text = cv_text
        cv.extraction_status = ExtractionStatus.COMPLETED

    job = application.job
    state = ScreeningState(
        cv_text=cv_text,
        job_title=job.title,
        job_description=_build_job_description(application),
        application_id=application.application_id,
        candidate_id=str(application.candidate_id),
        ai_mode=True,
        model=f"ollama/{settings.OLLAMA_MODEL}",
    )

    result = graph.invoke(state.as_plain())
    recomm = result["recommendation"]
    matched = [
        {
            "requirement": m.requirement,
            "status": m.status,
            "evidence": m.evidence,
            "is_mandatory": m.is_mandatory,
        }
        for m in result["matched_requirements"]
    ]
    missing = [
        {
            "requirement": m["requirement"],
            "status": "MISSING",
            "evidence": m["evidence"],
        }
        for m in matched
        if m["status"] == "MISSING"
    ]
    uncertain = [
        {
            "requirement": u.issue,
            "status": "UNCLEAR",
            "evidence": None,
        }
        for u in result["uncertainties"]
    ]

    screening = ScreeningResult(
        application_id=application.id,
        recommendation=Recommendation(recomm.recommendation),
        score=Decimal(recomm.score),
        evidence={"items": matched, "reason": recomm.reason},
        missing_requirements={"items": missing},
        uncertainty={
            "items": uncertain,
            "requires_hr_review": recomm.requires_hr_review,
        },
        model=result.get("model") or f"ollama/{settings.OLLAMA_MODEL}",
        hr_decision=HRDecision.PENDING,
    )
    db.add(screening)

    from app.db.models.application import ApplicationStatusHistory

    old = application.status
    application.status = ApplicationStatus.HR_REVIEW
    history = ApplicationStatusHistory(
        application_id=application.id,
        from_status=old.value if old else None,
        to_status=ApplicationStatus.HR_REVIEW.value,
        changed_by=None,
        reason=f"AI screening completed: {recomm.recommendation} ({recomm.score}/100)",
    )
    db.add(history)
    db.commit()
    db.refresh(screening)
    application.screening_results.append(screening)
    return screening