"""Adapter that runs the LangGraph screening workflow against a DB application.

The `ai` package lives at the repository root. The FastAPI backend runs from
`apps/backend`, so we make the repo root importable here.
"""
import sys
import threading
from decimal import Decimal
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[4]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from sqlalchemy.orm import Session

from ai.graphs.screening import graph
from ai.schemas import ScreeningState

from app.core.config import settings
from app.core.observability import invoke_graph, set_span_io, traced
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


def _is_uncertain(result: dict) -> bool:
    """A screening is ambiguous when UNCLEAR or carries unresolved uncertainties."""
    recomm = result.get("recommendation")
    if recomm is not None and getattr(recomm, "recommendation", None) == "UNCLEAR":
        return True
    if result.get("uncertainties"):
        return True
    return False


def _run_graph(
    *,
    cv_text: str,
    job_title: str | None,
    job_description: str,
    application_id: str | None,
    candidate_id: str | None,
    model: str,
) -> dict:
    state = ScreeningState(
        cv_text=cv_text,
        job_title=job_title,
        job_description=job_description,
        application_id=application_id,
        candidate_id=candidate_id,
        ai_mode=True,
        model=f"ollama/{model}",
        profile_model=f"ollama/{settings.OLLAMA_PROFILE_MODEL or settings.OLLAMA_MODEL}",
    )
    return invoke_graph(graph, state.as_plain())


def _run_graph_capped(
    *,
    cv_text: str,
    job_title: str | None,
    job_description: str,
    application_id: str | None,
    candidate_id: str | None,
    model: str,
    timeout_seconds: float,
) -> dict:
    """Run the LangGraph pipeline under a hard wall-clock deadline.

    The graph makes several Ollama calls in sequence; when Ollama is cold the
    total can stretch to many minutes. The auto-evaluation path caps this and
    falls back to the bounded legacy screening so a CV never waits forever.
    Only the AI phase runs in the thread — the caller owns the DB session.
    """
    box: list[dict] = []
    errors: list[BaseException] = []

    def _target() -> None:
        try:
            box.append(
                _run_graph(
                    cv_text=cv_text,
                    job_title=job_title,
                    job_description=job_description,
                    application_id=application_id,
                    candidate_id=candidate_id,
                    model=model,
                )
            )
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    thread = threading.Thread(target=_target, daemon=True)
    thread.start()
    thread.join(timeout_seconds)
    if thread.is_alive():
        raise TimeoutError(
            f"Screening graph exceeded {timeout_seconds}s on model {model}"
        )
    if errors:
        raise errors[0]
    return box[0]


@traced("cv-screening")
def screen_application(db: Session, application: Application) -> ScreeningResult:
    """Run the LangGraph workflow and persist the result as a ScreeningResult.

    Screening runs on Qwen3-8B Q4. Ambiguous (UNCLEAR) cases are only re-run on
    the second-opinion model when OLLAMA_FALLBACK_EVALUATION_MODEL is set.
    """
    set_span_io(
        input={
            "application_id": str(application.application_id),
            "candidate_id": str(application.candidate_id),
            "job_id": str(application.job_id),
            "capped": False,
        }
    )
    return _screen_with(db, application, _run_graph)


@traced("cv-screening-capped")
def screen_application_capped(
    db: Session,
    application: Application,
    timeout_seconds: float | None = None,
) -> ScreeningResult:
    """Run LangGraph screening under a hard wall-clock deadline.

    Used by the auto-evaluation path so a slow/hung Ollama call never blocks
    screening forever. On timeout raises TimeoutError so the caller can fall
    back to the bounded legacy screening. If the cap is 0 it behaves like the
    uncapped version.
    """
    set_span_io(
        input={
            "application_id": str(application.application_id),
            "candidate_id": str(application.candidate_id),
            "job_id": str(application.job_id),
            "timeout_seconds": timeout_seconds,
            "capped": True,
        }
    )
    timeout = (
        timeout_seconds
        if timeout_seconds is not None
        else settings.AUTO_SCREEN_TIMEOUT_SECONDS
    )

    def _runner(
        *,
        cv_text: str,
        job_title: str | None,
        job_description: str,
        application_id: str | None,
        candidate_id: str | None,
        model: str,
    ) -> dict:
        return _run_graph_capped(
            cv_text=cv_text,
            job_title=job_title,
            job_description=job_description,
            application_id=application_id,
            candidate_id=candidate_id,
            model=model,
            timeout_seconds=timeout,
        )

    return _screen_with(db, application, _runner)


def _screen_with(
    db: Session,
    application: Application,
    run_graph,
) -> ScreeningResult:
    """Shared screening body. ``run_graph`` is the graph executor (uncapped or
    capped); the caller owns the DB session and catches timeout exceptions."""
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
    result = run_graph(
        cv_text=cv_text,
        job_title=job.title,
        job_description=_build_job_description(application),
        application_id=application.application_id,
        candidate_id=str(application.candidate_id),
        model=settings.OLLAMA_EVALUATION_MODEL,
    )

    fallback_used = False
    if (
        _is_uncertain(result)
        and settings.OLLAMA_FALLBACK_EVALUATION_MODEL.strip()
    ):
        fallback_used = True
        result = run_graph(
            cv_text=cv_text,
            job_title=job.title,
            job_description=_build_job_description(application),
            application_id=application.application_id,
            candidate_id=str(application.candidate_id),
            model=settings.OLLAMA_FALLBACK_EVALUATION_MODEL,
        )

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
        model=result.get("model") or f"ollama/{settings.OLLAMA_EVALUATION_MODEL}",
        hr_decision=HRDecision.PENDING,
    )
    if fallback_used:
        screening.evidence = {
            **screening.evidence,
            "fallback_used": True,
            "fallback_model": f"ollama/{settings.OLLAMA_FALLBACK_EVALUATION_MODEL}",
        }

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
    set_span_io(
        output={
            "application_id": str(application.application_id),
            "recommendation": recomm.recommendation,
            "score": recomm.score,
            "model": screening.model,
            "fallback_used": fallback_used,
        }
    )
    return screening