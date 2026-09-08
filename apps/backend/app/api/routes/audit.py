import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, require_admin
from app.db.models import User
from app.db.models.audit_log import AuditLog

router = APIRouter(prefix="/audit-logs", tags=["Audit Logs"])


def _out(entry: AuditLog) -> dict:
    return {
        "id": entry.id,
        "user_id": str(entry.user_id) if entry.user_id else None,
        "action": entry.action,
        "entity_type": entry.entity_type,
        "entity_id": str(entry.entity_id) if entry.entity_id else None,
        "old_value": entry.old_value,
        "new_value": entry.new_value,
        "created_at": entry.created_at,
    }


@router.get("")
def list_audit_logs(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
    entity_type: str | None = None,
    action: str | None = None,
    limit: int = 100,
):
    query = db.query(AuditLog).order_by(AuditLog.created_at.desc())
    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type)
    if action:
        query = query.filter(AuditLog.action == action)
    rows = query.limit(limit).all()
    return [_out(r) for r in rows]