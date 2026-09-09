from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, require_hr_or_admin
from app.db.models.user import User
from app.schemas.settings import OrgSettingsOut, OrgSettingsUpdate
from app.services import settings_service

router = APIRouter(prefix="/settings", tags=["Settings"])


@router.get("/organization", response_model=OrgSettingsOut)
def get_organization(
    db: Session = Depends(get_db),
    _: User = Depends(require_hr_or_admin),
):
    """Company / HR identity used in AI-drafted emails."""
    company, hr = settings_service.org_identity(db)
    return OrgSettingsOut(company_name=company, hr_name=hr)


@router.put("/organization", response_model=OrgSettingsOut)
def update_organization(
    data: OrgSettingsUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_hr_or_admin),
):
    """Save company / HR identity. Takes effect immediately for new drafts."""
    row = settings_service.save_org_settings(
        db, company_name=data.company_name, hr_name=data.hr_name
    )
    return OrgSettingsOut(company_name=row.company_name, hr_name=row.hr_name)