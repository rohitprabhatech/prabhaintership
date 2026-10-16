from datetime import datetime
from uuid import UUID

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Index, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        CheckConstraint("length(btrim(action)) > 0", name="ck_audit_action_not_blank"),
        CheckConstraint("outcome IN ('success', 'failure', 'denied')", name="ck_audit_outcome"),
        CheckConstraint("jsonb_typeof(metadata) = 'object'", name="ck_audit_metadata_object"),
        Index("ix_audit_logs_time", text("occurred_at DESC"), text("audit_log_id DESC")),
        Index(
            "ix_audit_logs_target_time",
            "target_type",
            "target_id",
            text("occurred_at DESC"),
            postgresql_where=text("target_type IS NOT NULL AND target_id IS NOT NULL"),
        ),
        Index(
            "ix_audit_logs_actor_time",
            "actor_admin_id",
            text("occurred_at DESC"),
            postgresql_where=text("actor_admin_id IS NOT NULL"),
        ),
        {"schema": "internship_management"},
    )

    audit_log_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    actor_admin_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(
            "internship_management.admins.admin_id",
            name="fk_audit_logs_actor_admins",
            ondelete="RESTRICT",
        ),
    )
    action: Mapped[str] = mapped_column(Text, nullable=False)
    target_type: Mapped[str | None] = mapped_column(Text)
    target_id: Mapped[int | None] = mapped_column(BigInteger)
    outcome: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'success'"))
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.transaction_timestamp()
    )
    request_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))
    metadata_: Mapped[dict] = mapped_column(
        "metadata", JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
