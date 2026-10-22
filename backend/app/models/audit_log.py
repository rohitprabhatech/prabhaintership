from datetime import datetime
from uuid import UUID

from sqlalchemy import BigInteger, CheckConstraint, JSON, String, Uuid, ForeignKey, Index, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, DATABASE_SCHEMA
from app.db.types import UTCDateTime


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        CheckConstraint("length(trim(action)) > 0", name="ck_audit_action_not_blank"),
        CheckConstraint("outcome IN ('success', 'failure', 'denied')", name="ck_audit_outcome"),
        CheckConstraint("JSON_TYPE(metadata) = 'OBJECT'", name="ck_audit_metadata_object"),
        Index("ix_audit_logs_time", text("occurred_at DESC"), text("audit_log_id DESC")),
        Index(
            "ix_audit_logs_target_time",
            "target_type",
            "target_id",
            text("occurred_at DESC"),
        ),
        Index(
            "ix_audit_logs_actor_time",
            "actor_admin_id",
            text("occurred_at DESC"),
        ),
        {"schema": DATABASE_SCHEMA},
    )

    audit_log_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    actor_admin_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(
            f"{DATABASE_SCHEMA}.admins.admin_id",
            name="fk_audit_logs_actor_admins",
            ondelete="RESTRICT",
        ),
    )
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    target_type: Mapped[str | None] = mapped_column(String(64))
    target_id: Mapped[int | None] = mapped_column(BigInteger)
    outcome: Mapped[str] = mapped_column(String(16), nullable=False, server_default=text("'success'"))
    occurred_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, server_default=func.current_timestamp()
    )
    request_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True))
    metadata_: Mapped[dict] = mapped_column(
        "metadata", JSON, nullable=False, server_default=text("(JSON_OBJECT())")
    )
    actor_admin: Mapped["Admin | None"] = relationship("Admin", back_populates="audit_logs")
