from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Text,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CertificateEvent(Base):
    __tablename__ = "certificate_events"
    __table_args__ = (
        CheckConstraint(
            "event_type IN ('replaced', 'revoked', 'corrected')",
            name="ck_certificate_events_type",
        ),
        CheckConstraint(
            "related_certificate_id IS NULL OR related_certificate_id <> certificate_id",
            name="ck_certificate_events_not_self_related",
        ),
        CheckConstraint("length(btrim(reason)) > 0", name="ck_certificate_events_reason"),
        CheckConstraint(
            "(event_type = 'replaced' AND related_certificate_id IS NOT NULL) "
            "OR (event_type IN ('revoked', 'corrected') AND related_certificate_id IS NULL)",
            name="ck_certificate_events_related",
        ),
        Index(
            "ix_certificate_events_certificate_time",
            "certificate_id",
            text("occurred_at DESC"),
            text("certificate_event_id DESC"),
        ),
        Index(
            "ux_certificate_events_one_terminal_state",
            "certificate_id",
            unique=True,
            postgresql_where=text("event_type IN ('replaced', 'revoked')"),
        ),
        {"schema": "internship_management"},
    )

    certificate_event_id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    certificate_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "internship_management.certificates.certificate_id",
            name="fk_certificate_events_certificates",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    related_certificate_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(
            "internship_management.certificates.certificate_id",
            name="fk_certificate_events_related_certificates",
            ondelete="RESTRICT",
        ),
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.transaction_timestamp()
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    recorded_by: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "internship_management.admins.admin_id",
            name="fk_certificate_events_recorded_by_admins",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.transaction_timestamp()
    )
