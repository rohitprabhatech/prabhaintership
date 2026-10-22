from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    CHAR,
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, DATABASE_SCHEMA
from app.db.types import UTCDateTime


class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_payments_amount"),
        CheckConstraint("currency = 'INR'", name="ck_payments_currency"),
        CheckConstraint(
            "payment_method IN ('cash', 'bank_transfer', 'upi', 'card', 'cheque', 'other')",
            name="ck_payments_method",
        ),
        UniqueConstraint("payment_id", "enrollment_id", name="uq_payments_id_enrollment"),
        CheckConstraint(
            "payment_reference IS NULL OR length(trim(payment_reference)) > 0",
            name="ck_payments_reference_not_blank",
        ),
        Index("ux_payments_idempotency_key", "idempotency_key", unique=True),
        Index(
            "ux_payments_method_reference",
            "payment_method",
            "payment_reference",
            unique=True,
        ),
        Index(
            "ix_payments_enrollment_paid_at", "enrollment_id", text("paid_at DESC"), "payment_id"
        ),
        {"schema": DATABASE_SCHEMA},
    )

    payment_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    enrollment_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            f"{DATABASE_SCHEMA}.enrollments.enrollment_id",
            name="fk_payments_enrollments",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    idempotency_key: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(CHAR(3), nullable=False, server_default=text("'INR'"))
    paid_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    payment_method: Mapped[str] = mapped_column(String(32), nullable=False)
    payment_reference: Mapped[str | None] = mapped_column(String(256))
    recorded_by: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            f"{DATABASE_SCHEMA}.admins.admin_id",
            name="fk_payments_recorded_by_admins",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, server_default=func.current_timestamp()
    )
    enrollment: Mapped["Enrollment"] = relationship("Enrollment", back_populates="payments")
