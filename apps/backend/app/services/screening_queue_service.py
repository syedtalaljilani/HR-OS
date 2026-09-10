"""Persistent background screening queue.

Decouples AI screening from HTTP request lifecycles so screening keeps running
even when the HR user changes pages or refreshes the dashboard, and so backend
restarts do not silently abandon jobs.

Trigger points share one path:

- Application submitted (AUTO / EVALUATE): CV processing + AI screening +
  auto-reject policy, exactly the old auto-evaluation behaviour.
- HR clicks "Run AI screening" (MANUAL / SCREEN): AI screening only.
- HR clicks "Process CV" (MANUAL / PROCESS): CV processing only.

A daemon worker (``start_worker``) picks QUEUED entries oldest-first, marks them
PROCESSING (committed *before* the long Ollama work starts, so the dashboard
shows live progress), and finalises COMPLETED / FAILED when done.
"""
import logging
import threading
import time
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models.application import Application, ScreeningQueue
from app.db.models.enums import ScreeningQueueStatus

logger = logging.getLogger("hros.screening-queue")

# ACTION values stored on the queue row.
ACTION_EVALUATE = "EVALUATE"
ACTION_SCREEN = "SCREEN"
ACTION_PROCESS = "PROCESS"

# SOURCE values stored on the queue row.
SOURCE_AUTO = "AUTO"
SOURCE_MANUAL = "MANUAL"

# How often the worker polls for queued work.
_POLL_SECONDS = 5


def _has_active_entry(db: Session, application_id: uuid.UUID, action: str) -> bool:
    """True when the application already has a pending/running entry for action."""
    return (
        db.query(ScreeningQueue.id)
        .filter(
            ScreeningQueue.application_id == application_id,
            ScreeningQueue.action == action,
            ScreeningQueue.status.in_(
                (ScreeningQueueStatus.QUEUED, ScreeningQueueStatus.PROCESSING)
            ),
        )
        .first()
        is not None
    )


def is_application_screening(db: Session, application_id: uuid.UUID) -> bool:
    """True when the application has an active auto/manual screening job."""
    return _has_active_entry(db, application_id, ACTION_SCREEN) or _has_active_entry(
        db, application_id, ACTION_EVALUATE
    )


def enqueue(
    db: Session,
    application: Application,
    *,
    source: str = SOURCE_AUTO,
    action: str = ACTION_EVALUATE,
) -> ScreeningQueue:
    """Create a QUEUED work item for an application and commit it.

    Returns the existing active entry when one is already queued/running for the
    same application+action (dedupe, so double-clicks do not queue twice).
    """
    if application.deleted_at is not None:
        raise ValueError("Cannot queue work for a deleted application")

    existing = (
        db.query(ScreeningQueue)
        .filter(
            ScreeningQueue.application_id == application.id,
            ScreeningQueue.action == action,
            ScreeningQueue.status.in_(
                (ScreeningQueueStatus.QUEUED, ScreeningQueueStatus.PROCESSING)
            ),
        )
        .order_by(ScreeningQueue.queued_at.desc())
        .first()
    )
    if existing is not None:
        return existing

    # A fresh job invalidates any older failed attempts for the same
    # application+action, so prune them to keep the dashboard honest.
    stale = (
        db.query(ScreeningQueue)
        .filter(
            ScreeningQueue.application_id == application.id,
            ScreeningQueue.action == action,
            ScreeningQueue.status == ScreeningQueueStatus.FAILED,
        )
        .all()
    )
    for row in stale:
        db.delete(row)

    entry = ScreeningQueue(
        application_id=application.id,
        job_id=application.job_id,
        candidate_name=application.candidate.full_name
        if application.candidate
        else None,
        job_title=application.job.title if application.job else None,
        source=source,
        action=action,
        status=ScreeningQueueStatus.QUEUED,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


# --------------------------------------------------------------------------- #
# Worker
# --------------------------------------------------------------------------- #
def _finalise_entry(
    entry: ScreeningQueue,
    *,
    ok: bool,
    score: object = None,
    recommendation: str | None = None,
    error_message: str | None = None,
) -> None:
    entry.status = (
        ScreeningQueueStatus.COMPLETED if ok else ScreeningQueueStatus.FAILED
    )
    entry.completed_at = datetime.now(timezone.utc)
    entry.score = score
    entry.recommendation = recommendation
    entry.error_message = error_message


def _execute_entry(db: Session, entry: ScreeningQueue) -> None:
    """Run the queued work for ``entry`` on the caller's session."""
    application = db.get(Application, entry.application_id)
    if application is None:
        _finalise_entry(
            entry, ok=False, error_message="Application no longer exists"
        )
        db.commit()
        return

    if application.deleted_at is not None:
        _finalise_entry(
            entry, ok=False, error_message="Application was deleted"
        )
        db.commit()
        return

    if entry.action == ACTION_PROCESS:
        from app.services import screening_service

        screening_service.process_application(db, application)
        _finalise_entry(entry, ok=True)
        db.commit()
        return

    if entry.action == ACTION_SCREEN:
        from app.services import evaluation_service

        screening = evaluation_service._run_screen(db, application)
        _finalise_entry(
            entry,
            ok=True,
            score=float(screening.score) if screening.score is not None else None,
            recommendation=screening.recommendation.value
            if screening.recommendation
            else None,
        )
        db.commit()
        return

    # ACTION_EVALUATE — full auto-evaluation (process + screen + policy).
    from app.services import evaluation_service

    result = evaluation_service.auto_evaluate_application(db, application)
    _finalise_entry(
        entry,
        ok=bool(result.get("auto_evaluated")),
        score=result.get("score"),
        recommendation=result.get("recommendation"),
        error_message=result.get("error") if not result.get("auto_evaluated") else None,
    )
    db.commit()


def _process_one() -> bool:
    """Pop one QUEUED entry and run it. Returns True when work was done."""
    from app.db.session import SessionLocal

    with SessionLocal() as db:
        entry = (
            db.query(ScreeningQueue)
            .filter(ScreeningQueue.status == ScreeningQueueStatus.QUEUED)
            .order_by(ScreeningQueue.queued_at.asc())
            .first()
        )
        if entry is None:
            return False

        entry.status = ScreeningQueueStatus.PROCESSING
        entry.started_at = datetime.now(timezone.utc)
        db.commit()

        try:
            _execute_entry(db, entry)
            logger.info(
                "screening-queue processed %s (%s/%s) -> %s",
                entry.application_id,
                entry.source,
                entry.action,
                entry.status.value,
            )
        except Exception:
            logger.exception(
                "screening-queue entry %s failed", entry.id
            )
            db.rollback()
            entry = db.get(ScreeningQueue, entry.id)
            if entry is not None:
                _finalise_entry(
                    entry,
                    ok=False,
                    error_message="Screening crashed: see server logs",
                )
                db.commit()
        return True


def _worker_body() -> None:
    while True:
        time.sleep(_POLL_SECONDS)
        try:
            while _process_one():
                pass
        except Exception:
            logger.exception("screening-queue worker tick failed")


def start_worker() -> None:
    """Start the background screening worker (idempotent-ish daemon thread)."""
    threading.Thread(
        target=_worker_body, daemon=True, name="screening-queue-worker"
    ).start()