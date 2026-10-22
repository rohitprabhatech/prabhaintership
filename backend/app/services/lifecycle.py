from uuid import UUID

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


def audit_lifecycle_action(
    session: Session,
    *,
    admin_id: int,
    action: str,
    target_type: str,
    target_id: int,
    reason: str,
    request_id: UUID | None = None,
    metadata: dict | None = None,
) -> None:
    audit_metadata = dict(metadata or {})
    audit_metadata["reason"] = reason
    session.add(
        AuditLog(
            actor_admin_id=admin_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            request_id=request_id,
            metadata_=audit_metadata,
        )
    )
