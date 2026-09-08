import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, require_hr_or_admin
from app.db.models import Application, User
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
from app.services import application_service, screening_service

router = APIRouter(prefix="/applications", tags=["Applications"])


def _get_application(db: Session, application_id: uuid.UUID) -> Application:
    application = db.get(Application, application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found")
    return application


@router.get("", response_model=list[ApplicationOut])
def list_applications(
    db: Session = Depends(get_db),
    _: User = Depends(require_hr_or_admin),
):
    applications = (
        db.query(Application).order_by(Application.created_at.desc()).all()
    )
    return [ApplicationOut.model_validate(a) for a in applications]


@router.get("/{application_id}", response_model=ApplicationDetail)
def get_application(
    application_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_hr_or_admin),
):
    application = _get_application(db, application_id)
    return _to_detail(application)


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
    return ApplicationDetail(
        **ApplicationOut.model_validate(application).model_dump(),
        candidate_name=application.candidate.full_name,
        candidate_email=application.candidate.email,
        candidate_phone=application.candidate.phone,
        job_title=application.job.title,
        cv_documents=cv_docs,
        screening=screening,
        status_history=history,
    )


@router.post("/{application_id}/process", response_model=dict)
def process_application(
    application_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_hr_or_admin),
):
    application = _get_application(db, application_id)
    return screening_service.process_application(db, application)


@router.post("/{application_id}/screen", response_model=ScreeningOut)
def screen_application(
    application_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_hr_or_admin),
):
    application = _get_application(db, application_id)
    screening = screening_service.screen_application(db, application)
    return ScreeningOut.model_validate(screening)


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
    screening.recommendation = data.recommendation
    if data.score is not None:
        from decimal import Decimal

        screening.score = Decimal(data.score)
    screening.hr_decision = HRDecision.OVERRIDDEN
    screening.reviewed_by = current_user.id
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
        db, application, data.status, current_user.id, data.reason
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
        db, application, data.decision, current_user.id, data.reason
    )
    db.refresh(application)
    return ApplicationOut.model_validate(application)