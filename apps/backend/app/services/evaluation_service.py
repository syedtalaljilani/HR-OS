"""Automatic evaluation of applications when they are submitted.

Runs CV processing + AI screening right after a candidate applies, computes a
score, and applies the configured policy:

- score below AUTO_REJECT_THRESHOLD  -> status REJECTED + rejection email w/ reason
- score at/above threshold           -> status HR_REVIEW (AI recommends, HR decides)

That threshold is fixed at 40: anything below is auto-rejected, everything at or
above lands on the dashboard for human review and a possible interview call. The
applicant never gets SELECTED automatically; only recommendations and low-score
rejections are automated, and HR can revert any of them.
"""
import logging
import uuid

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models.application import Application, ScreeningResult
from app.db.models.enums import ApplicationStatus, Recommendation
from app.services import application_service, screening_service

logger = logging.getLogger("hros.evaluation")


def _run_screen(db: Session, application: Application) -> ScreeningResult:
    """Run LangGraph screening under a hard timeout with a fallback to the
    legacy service when the graph is slow, hangs, or fails outright."""
    from app.services import langgraph_screening_service

    try:
        return langgraph_screening_service.screen_application_capped(
            db,
            application,
            timeout_seconds=settings.AUTO_SCREEN_TIMEOUT_SECONDS,
        )
    except Exception:
        logger.exception(
            "LangGraph screening failed for %s; falling back to legacy service",
            application.application_id,
        )
        db.rollback()
        return screening_service.screen_application(db, application)


def auto_evaluate_application(db: Session, application: Application) -> dict:
    """Process + screen an application and apply the auto-reject policy."""
    screening_service.process_application(db, application)

    try:
        screening = _run_screen(db, application)
    except Exception:
        logger.exception(
            "Auto-evaluation failed for %s; leaving for manual review",
            application.application_id,
        )
        return {"auto_evaluated": False, "error": "screening_failed"}

    score = float(screening.score or 0)
    threshold = settings.AUTO_REJECT_THRESHOLD
    reason = None
    rank = None

    requires_human = _requires_human_review(screening)
    # Auto-reject every application scoring below the threshold — no exceptions
    # for uncertain cases. Candidates at/above 40 always go to HR review; the
    # AI "requires human" flag is still reported for information.
    if score < threshold:
        rank, total_candidates = application_rank_in_job(db, application)
        detail = _rejection_reason(application, screening)
        reason = f"AI auto-rejection (score {score:.0f}/100 below {threshold}): {detail}"
        email_subject = None
        email_body = None
        try:
            draft = _draft_rejection_email(
                db, application, screening, detail, rank, total_candidates
            )
            email_subject = draft.get("subject")
            email_body = draft.get("body")
        except Exception:
            logger.exception(
                "AI email draft failed for %s; using deterministic body",
                application.application_id,
            )
        application_service.change_status(
            db,
            application,
            ApplicationStatus.REJECTED,
            changed_by=None,
            reason=reason,
            email_reason=detail,
            email_context={
                "score": score,
                "rank": rank,
                "total_candidates": total_candidates,
            },
            email_subject=email_subject,
            email_body=email_body,
            send_email=True,
        )

    return {
        "auto_evaluated": True,
        "score": score,
        "recommendation": screening.recommendation.value,
        "status": application.status.value,
        "rejected": application.status == ApplicationStatus.REJECTED,
        "reason": reason,
        "requires_human_review": requires_human,
        "rank": rank if score < threshold else None,
    }


def application_rank_in_job(db: Session, application: Application) -> tuple[int, int]:
    """Return (rank, total_scored) of an application within its job's leaderboard."""
    ranked = rank_applications(db, job_id=application.job_id, limit=1000)
    total = len(ranked)
    for index, row in enumerate(ranked, start=1):
        if row["id"] == application.id:
            return index, total
    return max(total, 1), total


def _requires_human_review(screening: ScreeningResult) -> bool:
    """Auto-reject only on clear evidence; defer uncertain cases to HR."""
    uncertainty = screening.uncertainty or {}
    items = uncertainty.get("items") or []
    if items:
        return True
    if uncertainty.get("requires_hr_review"):
        return True
    return False


def _rejection_reason(application: Application, screening: ScreeningResult) -> str:
    """Build a candidate-facing rejection reason from the screening evidence.

    Deliberately excludes internal score / threshold / AI wording so the text
    can be safely included in an email to the candidate while staying detailed
    about which requirements were not met.
    """
    evidence = screening.evidence or {}
    items = evidence.get("items") or []

    missing = []
    for item in items:
        if isinstance(item, dict) and item.get("status") == "MISSING":
            req = item.get("requirement")
            if req:
                missing.append(req)

    if missing:
        return (
            "After reviewing your application, we could not see clear evidence of "
            "several key requirements for this role: "
            + ", ".join(missing[:6])
            + "."
        )
    return (
        "After reviewing your application, we felt your profile did not align "
        "closely enough with the requirements of this role."
    )


def _draft_rejection_email(
    db: Session, application: Application, screening: ScreeningResult, reason: str, rank: int, total: int
) -> dict:
    """Draft an AI-generated rejection email (subject + body) with the email model.

    The reason (already candidate-facing) is rephrased into a warm message, and
    the missing requirements are provided as context so the email stays detailed
    but never leaks internal AI score/rank (architecture/evaluation.md).
    """
    from app.services import email_agent_service

    evidence = screening.evidence or {}
    items = evidence.get("items") or []
    missing = [
        str(item.get("requirement"))
        for item in items
        if isinstance(item, dict)
        and item.get("status") == "MISSING"
        and item.get("requirement")
    ]

    return email_agent_service.draft_email(
        email_type="REJECTED",
        candidate_name=application.candidate.full_name if application.candidate else None,
        job_title=application.job.title if application.job else None,
        reason=reason,
        context={"missing": missing[:6]} if missing else {},
        tone="warm",
        db=db,
    )


def rank_applications(
    db: Session, job_id: uuid.UUID | None = None, limit: int = 10
) -> list[dict]:
    """Return applications ordered by latest AI screening score (desc)."""
    from app.db.models.application import ApplicationStatusHistory

    query = db.query(Application)
    query = query.filter(Application.deleted_at.is_(None))
    if job_id is not None:
        query = query.filter(Application.job_id == job_id)

    applications = query.order_by(Application.created_at.desc()).all()

    auto_rejected_ids: set[uuid.UUID] = set()
    rows = (
        db.query(ApplicationStatusHistory.application_id)
        .filter(
            ApplicationStatusHistory.to_status == ApplicationStatus.REJECTED.value,
            ApplicationStatusHistory.reason.like("AI auto%"),
        )
        .all()
    )
    auto_rejected_ids = {row[0] for row in rows}

    ranked = []
    for app in applications:
        screening = app.screening_results[-1] if app.screening_results else None
        ranked.append(
            {
                "id": app.id,
                "application_id": app.application_id,
                "candidate_id": app.candidate_id,
                "job_id": app.job_id,
                "candidate_name": app.candidate.full_name if app.candidate else None,
                "candidate_email": app.candidate.email if app.candidate else None,
                "job_title": app.job.title if app.job else None,
                "status": app.status.value,
                "created_at": app.created_at.isoformat() if app.created_at else None,
                "score": (
                    float(screening.score)
                    if screening and screening.score is not None
                    else None
                ),
                "recommendation": (
                    screening.recommendation.value if screening else None
                ),
                "auto_rejected": (
                    app.status == ApplicationStatus.REJECTED
                    and app.id in auto_rejected_ids
                ),
            }
        )

    scored = [a for a in ranked if a["score"] is not None]
    unsorted = [a for a in ranked if a["score"] is None]
    scored.sort(key=lambda a: a["score"], reverse=True)
    ranked = scored + unsorted
    return ranked[:limit]


def run_auto_evaluation(application_id: uuid.UUID) -> None:
    """Queue a full auto-evaluation (process + screen + auto-reject policy).

    Kept as a thin wrapper for backward compatibility — the actual work runs in
    the persistent background screening worker, surviving page changes, refreshes
    and (to a point) backend restarts.
    """
    from app.db.database import SessionLocal
    from app.db.models.application import Application
    from app.services import screening_queue_service

    db = SessionLocal()
    try:
        application = db.get(Application, application_id)
        if application is None:
            logger.warning(
                "Auto-evaluation skipped: application %s not found", application_id
            )
            return
        screening_queue_service.enqueue(
            db,
            application,
            source=screening_queue_service.SOURCE_AUTO,
            action=screening_queue_service.ACTION_EVALUATE,
        )
        logger.info("Auto-evaluation queued for %s", application.application_id)
    except Exception:
        logger.exception("Failed to queue auto-evaluation for %s", application_id)
        db.rollback()
    finally:
        db.close()