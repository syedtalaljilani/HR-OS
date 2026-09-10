import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.dependencies import get_db, require_hr_or_admin
from app.db.models import ScreeningQueue, User
from app.db.models.enums import ScreeningQueueStatus

router = APIRouter(prefix="/screening-queue", tags=["Screening Queue"])

# A PROCESSING entry older than the screening deadline plus a safety margin is
# never coming back (server restarted / worker thread died), so it is marked
# FAILED so the dashboard shows the truth.
_STALE_BUFFER_SECONDS = 60


def _recover_stale_entries(db: Session, now: datetime | None = None) -> None:
    if settings.AUTO_SCREEN_TIMEOUT_SECONDS <= 0:
        return
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(
        seconds=settings.AUTO_SCREEN_TIMEOUT_SECONDS + _STALE_BUFFER_SECONDS
    )
    stale = (
        db.query(ScreeningQueue)
        .filter(
            ScreeningQueue.status == ScreeningQueueStatus.PROCESSING,
            ScreeningQueue.started_at < cutoff,
        )
        .all()
    )
    if not stale:
        return
    for entry in stale:
        entry.status = ScreeningQueueStatus.FAILED
        entry.completed_at = now
        entry.error_message = (
            "Screening exceeded the timeout and was abandoned (still marked FAILED "
            "after server restart)"
        )
    db.commit()


class ScreeningQueueOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    application_id: uuid.UUID
    job_id: uuid.UUID
    candidate_name: str | None
    job_title: str | None
    source: str
    action: str
    status: ScreeningQueueStatus
    score: float | None
    recommendation: str | None
    error_message: str | None
    queued_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


@router.get("", response_model=list[ScreeningQueueOut])
def list_screening_queue(
    db: Session = Depends(get_db),
    _: User = Depends(require_hr_or_admin),
    status: ScreeningQueueStatus | None = None,
    limit: int = Query(default=50, ge=1, le=200),
):
    """List screening queue entries, newest first.

    Optionally filter by status (QUEUED, PROCESSING, COMPLETED, FAILED).
    Stale PROCESSING entries (past the screening deadline) are recovered to
    FAILED before returning so the queue never shows a permanent "processing".
    """
    _recover_stale_entries(db)
    query = db.query(ScreeningQueue).order_by(desc(ScreeningQueue.queued_at))
    if status is not None:
        query = query.filter(ScreeningQueue.status == status)
    entries = query.limit(limit).all()
    return [ScreeningQueueOut.model_validate(e) for e in entries]


@router.get("/stats")
def screening_queue_stats(
    db: Session = Depends(get_db),
    _: User = Depends(require_hr_or_admin),
):
    """Return counts for each screening queue status."""
    from sqlalchemy import func

    _recover_stale_entries(db)
    rows = (
        db.query(ScreeningQueue.status, func.count())
        .group_by(ScreeningQueue.status)
        .all()
    )
    stats = {status.value: 0 for status in ScreeningQueueStatus}
    for status, count in rows:
        stats[status.value] = count
    stats["total"] = sum(stats.values())
    return stats
