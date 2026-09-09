"""Organization-level settings (company identity for AI email drafting)."""
from sqlalchemy.orm import Session

from app.core.config import settings as app_settings
from app.db.models.org_settings import OrgSettings


def get_org_settings(db: Session) -> OrgSettings:
    """Return the single settings row, creating it (from env defaults) if absent."""
    row = db.get(OrgSettings, 1)
    if row is None:
        row = OrgSettings(
            id=1,
            company_name=app_settings.COMPANY_NAME,
            hr_name=app_settings.HR_NAME,
        )
        db.add(row)
        db.flush()
    return row


def org_identity(db: Session) -> tuple[str, str]:
    """Effective company/HR identity: DB value wins, env is the fallback."""
    row = get_org_settings(db)
    company = row.company_name or app_settings.COMPANY_NAME
    hr = row.hr_name or app_settings.HR_NAME
    return company, hr


def save_org_settings(
    db: Session, *, company_name: str = "", hr_name: str = ""
) -> OrgSettings:
    """Persist company identity. Called from the dashboard Settings page."""
    row = get_org_settings(db)
    row.company_name = (company_name or "").strip()
    row.hr_name = (hr_name or "").strip()
    db.commit()
    db.refresh(row)
    return row