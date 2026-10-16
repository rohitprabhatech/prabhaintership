from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PaymentAdjustment(Base):
    __tablename__ = "payment_adjustments"
    __table_args__ = (
        CheckConstraint(
            "adjustment_type IN ('refund', 'reversal')",
            name="ck_payment_adjustments_type",
        ),
        CheckConstraint("amount > 0", name="ck_payment_adjustments_amount"),
        CheckConstraint("length(btrim(reason)) > 0", name="ck_payment_adjustments_reason"),
        UniqueConstraint("idempotency_key", name="uq_payment_adjustments_idempotency_key"),
        Index("ix_payment_adjustments_payment_time", "payment_id", "occurred_at", "adjustment_id"),
        Index(
            "ux_payment_adjustments_one_reversal",
            "payment_id",
            unique=True,
            postgresql_where=text("adjustment_type = 'reversal'"),
        ),
        {"schema": "internship_management"},
    )

    adjustment_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    payment_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "internship_management.payments.payment_id",
            name="fk_payment_adjustments_payments",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    adjustment_type: Mapped[str] = mapped_column(Text, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    idempotency_key: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.transaction_timestamp()
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    recorded_by: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "internship_management.admins.admin_id",
            name="fk_payment_adjustments_recorded_by_admins",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.transaction_timestamp()
    )
