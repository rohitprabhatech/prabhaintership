from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Computed,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, DATABASE_SCHEMA
from app.db.types import UTCDateTime


class CertificateEvent(Base):
    __tablename__ = "certificate_events"
    __table_args__ = (
        CheckConstraint(
            "event_type IN ('replaced', 'revoked', 'corrected')",
            name="ck_certificate_events_type",
        ),
        CheckConstraint("length(trim(reason)) > 0", name="ck_certificate_events_reason"),
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
            "terminal_certificate_id",
            unique=True,
        ),
        {"schema": DATABASE_SCHEMA},
    )

    certificate_event_id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    certificate_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            f"{DATABASE_SCHEMA}.certificates.certificate_id",
            name="fk_certificate_events_certificates",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(16), nullable=False)
    terminal_certificate_id: Mapped[int | None] = mapped_column(
        BigInteger,
        Computed("CASE WHEN event_type IN ('replaced', 'revoked') THEN certificate_id ELSE NULL END", persisted=True),
    )
    related_certificate_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(
            f"{DATABASE_SCHEMA}.certificates.certificate_id",
            name="fk_certificate_events_related_certificates",
            ondelete="RESTRICT",
        ),
    )
    occurred_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, server_default=func.current_timestamp()
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    recorded_by: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            f"{DATABASE_SCHEMA}.admins.admin_id",
            name="fk_certificate_events_recorded_by_admins",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, server_default=func.current_timestamp()
    )
    certificate: Mapped["Certificate"] = relationship(
        "Certificate",
        back_populates="events",
        foreign_keys=[certificate_id],
    )
