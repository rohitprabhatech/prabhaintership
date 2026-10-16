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
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class FeeAdjustment(Base):
    __tablename__ = "fee_adjustments"
    __table_args__ = (
        CheckConstraint(
            "adjustment_type IN ('discount', 'fee_increase')",
            name="ck_fee_adjustments_type",
        ),
        CheckConstraint("amount > 0", name="ck_fee_adjustments_amount"),
        CheckConstraint("length(btrim(reason)) > 0", name="ck_fee_adjustments_reason"),
        UniqueConstraint("idempotency_key", name="uq_fee_adjustments_idempotency_key"),
        Index("ix_fee_adjustments_enrollment_time", "enrollment_id", "approved_at"),
        {"schema": "internship_management"},
    )

    fee_adjustment_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    enrollment_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "internship_management.enrollments.enrollment_id",
            name="fk_fee_adjustments_enrollments",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    adjustment_type: Mapped[str] = mapped_column(Text, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    idempotency_key: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    approved_by: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "internship_management.admins.admin_id",
            name="fk_fee_adjustments_approved_by_admins",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    approved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.transaction_timestamp()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.transaction_timestamp()
    )
