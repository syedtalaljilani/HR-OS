import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.config import settings

from app.core.dependencies import get_db, require_hr_or_admin, require_roles
from app.db.models import Application, User
from app.db.models.enums import UserRole
from app.db.models.enums import ApplicationStatus, HRDecision
from app.schemas.application import (
    ApplicationDetail,
    ApplicationHistoryOut,
    ApplicationOut,
    DecisionRequest,
    OverrideRequest,
    ScreeningOut,
    StatusUpdate,
)
from app.schemas.interview import InterviewCreate, InterviewOut
from app.services import application_service
from app.services import audit_service as audit
from app.services import settings_service
from app.utils.common import jsonify_data

router = APIRouter(prefix="/applications", tags=["Applications"])


def _get_application(
    db: Session, application_id: uuid.UUID, include_deleted: bool = False
) -> Application:
    application = db.get(Application, application_id)
    if application is None or (
        not include_deleted and application.deleted_at is not None
    ):
        raise HTTPException(status_code=404, detail="Application not found")
    return application


def _latest_screening(application: Application):
    if not application.screening_results:
        return None
    return max(
        application.screening_results,
        key=lambda s: s.created_at,
    )


@router.get("", response_model=list[ApplicationOut])
def list_applications(
    db: Session = Depends(get_db),
    _: User = Depends(require_hr_or_admin),
    score_min: float | None = None,
    status: ApplicationStatus | None = None,
    include_deleted: bool = False,
):
    """List applications, optionally filtered to those with a screening score
    at/above ``score_min`` (e.g. the 40-point human-review cut-off)."""
    query = db.query(Application).order_by(Application.created_at.desc())
    if not include_deleted:
        query = query.filter(Application.deleted_at.is_(None))
    if status is not None:
        query = query.filter(Application.status == status)
    applications = query.all()
    if score_min is not None:
        applications = [
            a
            for a in applications
            if (s := _latest_screening(a)) is not None
            and s.score is not None
            and float(s.score) >= score_min
        ]
    items = []
    for a in applications:
        item = ApplicationOut.model_validate(a).model_dump()
        if (latest := _latest_screening(a)) is not None:
            item["screening"] = ScreeningOut.model_validate(latest)
        items.append(ApplicationOut(**item))
    return items


@router.get("/ranked")
def list_ranked_applications(
    db: Session = Depends(get_db),
    _: User = Depends(require_hr_or_admin),
    job_id: uuid.UUID | None = None,
    limit: int = 10,
):
    from app.services import evaluation_service

    if limit < 1 or limit > 500:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 500")
    return evaluation_service.rank_applications(db, job_id=job_id, limit=limit)


@router.get("/{application_id}", response_model=ApplicationDetail)
def get_application(
    application_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_hr_or_admin),
    include_deleted: bool = False,
):
    application = _get_application(
        db, application_id, include_deleted=include_deleted
    )
    return _to_detail(application)


@router.get("/cv/{cv_id}/file")
def get_cv_file(
    cv_id: uuid.UUID,
    _: User = Depends(require_roles(UserRole.HR, UserRole.ADMIN, UserRole.INTERVIEWER)),
    db: Session = Depends(get_db),
):
    from app.db.models import CVDocument

    cv = db.get(CVDocument, cv_id)
    if cv is None:
        raise HTTPException(status_code=404, detail="CV document not found")

    path = Path(cv.file_path)
    if not path.is_absolute():
        path = Path(settings.UPLOAD_DIR) / "cvs" / path.name
    if not path.is_file():
        raise HTTPException(status_code=404, detail="CV file not found on disk")

    return FileResponse(
        path,
        media_type=cv.mime_type or "application/octet-stream",
        filename=cv.file_name,
    )


def _to_detail(application: Application) -> ApplicationDetail:
    from app.schemas.application import CVDocumentOut

    cv_docs = [
        CVDocumentOut.model_validate(cv) for cv in (application.cv_documents or [])
    ]
    history = [
        ApplicationHistoryOut.model_validate(h)
        for h in sorted(application.status_history or [], key=lambda h: h.created_at)
    ]
    screening = (
        ScreeningOut.model_validate(application.screening_results[-1])
        if application.screening_results
        else None
    )
    interviews = [
        InterviewOut.model_validate(i)
        for i in sorted(application.interviews or [], key=lambda i: i.created_at)
    ]
    return ApplicationDetail(
        **ApplicationOut.model_validate(application).model_dump(exclude={"screening"}),
        candidate_name=application.candidate.full_name,
        candidate_email=application.candidate.email,
        candidate_phone=application.candidate.phone,
        job_title=application.job.title,
        cv_documents=cv_docs,
        screening=screening,
        status_history=history,
        interviews=interviews,
    )


@router.post("/{application_id}/process")
def process_application(
    application_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_hr_or_admin),
):
    """Queue CV processing. Returns immediately; the background worker does the
    heavy extraction/AI work, so navigating away or refreshing the page does not
    cancel it."""
    from app.services import screening_queue_service

    application = _get_application(db, application_id)
    entry = screening_queue_service.enqueue(
        db,
        application,
        source=screening_queue_service.SOURCE_MANUAL,
        action=screening_queue_service.ACTION_PROCESS,
    )
    return {
        "queued": True,
        "status": entry.status.value,
        "entry_id": str(entry.id),
    }


@router.post("/{application_id}/screen")
def screen_application(
    application_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_hr_or_admin),
):
    """Queue an AI screening. Returns immediately; the background worker runs
    the LangGraph pipeline (under a deadline, with legacy fallback), so the
    screening survives page changes and refreshes and is visible in the
    dashboard screening queue."""
    from app.services import screening_queue_service

    application = _get_application(db, application_id)
    entry = screening_queue_service.enqueue(
        db,
        application,
        source=screening_queue_service.SOURCE_MANUAL,
        action=screening_queue_service.ACTION_SCREEN,
    )
    return {
        "queued": True,
        "status": entry.status.value,
        "entry_id": str(entry.id),
    }


@router.post("/{application_id}/override", response_model=ScreeningOut)
def override_screening(
    application_id: uuid.UUID,
    data: OverrideRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin),
):
    application = _get_application(db, application_id)
    if not application.screening_results:
        raise HTTPException(status_code=404, detail="No screening result to override")
    screening = application.screening_results[-1]
    old_recommendation = screening.recommendation
    screening.recommendation = data.recommendation
    if data.score is not None:
        from decimal import Decimal

        screening.score = Decimal(data.score)
    screening.hr_decision = HRDecision.OVERRIDDEN
    screening.reviewed_by = current_user.id
    db.flush()
    audit.log_action(
        db,
        user_id=current_user.id,
        action="screening.override",
        entity_type="screening_result",
        entity_id=screening.id,
        old_value={"recommendation": old_recommendation.value if old_recommendation else None},
        new_value={"recommendation": data.recommendation, "note": data.note},
    )
    db.commit()
    db.refresh(screening)
    return ScreeningOut.model_validate(screening)


@router.patch("/{application_id}/status", response_model=ApplicationOut)
def change_status(
    application_id: uuid.UUID,
    data: StatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin),
):
    application = _get_application(db, application_id)
    application_service.change_status(
        db,
        application,
        data.status,
        current_user.id,
        data.reason,
        send_email=True,
    )
    db.refresh(application)
    return ApplicationOut.model_validate(application)


@router.get("/{application_id}/history", response_model=list[ApplicationHistoryOut])
def get_history(
    application_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_hr_or_admin),
):
    application = _get_application(db, application_id)
    history = sorted(application.status_history or [], key=lambda h: h.created_at)
    return [ApplicationHistoryOut.model_validate(h) for h in history]


@router.get("/{application_id}/interviews", response_model=list[InterviewOut])
def list_interviews(
    application_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_hr_or_admin),
):
    application = _get_application(db, application_id)
    interviews = sorted(application.interviews or [], key=lambda i: i.created_at)
    return [InterviewOut.model_validate(i) for i in interviews]


@router.post(
    "/{application_id}/interview",
    response_model=InterviewOut,
    status_code=status.HTTP_201_CREATED,
)
def schedule_interview(
    application_id: uuid.UUID,
    data: InterviewCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin),
):
    """Schedule an interview call for a candidate (human review outcome).

    Moves the application to INTERVIEW_SCHEDULED and sends the candidate an
    INTERVIEW email with the scheduled time / location / notes.
    """
    from app.db.models.enums import InterviewStatus
    from app.db.models.interview import Interview

    application = _get_application(db, application_id)
    if data.scheduled_at <= datetime.now(timezone.utc):
        raise HTTPException(
            status_code=400,
            detail="Scheduled time must be in the future",
        )

    interview = Interview(
        application_id=application.id,
        type=data.type,
        scheduled_at=data.scheduled_at,
        location=data.location,
        notes=data.notes,
        status=InterviewStatus.SCHEDULED,
        created_by=current_user.id,
    )
    db.add(interview)
    db.flush()

    company_name, hr_name, company_location = settings_service.org_identity(db)
    application_service.change_status(
        db,
        application,
        ApplicationStatus.INTERVIEW_SCHEDULED,
        current_user.id,
        reason="Interview call scheduled",
        send_email=True,
        email_context={
            "interview": interview,
            "company_location": company_location,
            "company_name": company_name,
            "hr_contact": hr_name,
        },
    )
    db.refresh(interview)
    return InterviewOut.model_validate(interview)


@router.post("/{application_id}/decision", response_model=ApplicationOut)
def make_decision(
    application_id: uuid.UUID,
    data: DecisionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin),
):
    if data.decision not in (
        ApplicationStatus.SELECTED,
        ApplicationStatus.HOLD,
        ApplicationStatus.REJECTED,
    ):
        raise HTTPException(
            status_code=400,
            detail="Final decision must be SELECTED, HOLD or REJECTED",
        )
    application = _get_application(db, application_id)
    application_service.change_status(
        db,
        application,
        data.decision,
        current_user.id,
        data.reason,
        send_email=True,
    )
    if data.decision == ApplicationStatus.SELECTED:
        application_service.reject_other_applications_on_selection(
            db, application, changed_by=current_user.id, reason=data.reason
            or "Position filled — another candidate has been selected.",
        )
    db.refresh(application)
    return ApplicationOut.model_validate(application)


@router.delete("/{application_id}", response_model=ApplicationOut)
def delete_application(
    application_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin),
):
    """Soft-delete an application (recoverable). Every deletion is logged in
    the audit log and in the application's status history."""
    application = _get_application(db, application_id, include_deleted=True)
    return ApplicationOut.model_validate(
        application_service.delete_application(db, application, current_user.id)
    )


@router.post("/{application_id}/recover", response_model=ApplicationOut)
def recover_application(
    application_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin),
):
    """Restore a soft-deleted application back to the active list."""
    application = _get_application(db, application_id, include_deleted=True)
    return ApplicationOut.model_validate(
        application_service.recover_application(db, application, current_user.id)
    )