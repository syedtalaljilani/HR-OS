import uuid

from sqlalchemy.orm import Session

from app.db.models.audit_log import AuditLog


def log_action(
    db: Session,
    user_id: uuid.UUID | None,
    action: str,
    entity_type: str,
    entity_id: uuid.UUID | None,
    old_value: dict | None = None,
    new_value: dict | None = None,
) -> AuditLog:
    entry = AuditLog(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        old_value=old_value,
        new_value=new_value,
    )
    db.add(entry)
    db.flush()
    return entry


def commit_with_audit(db: Session) -> None:
    db.commit()