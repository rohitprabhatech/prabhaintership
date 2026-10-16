from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CHAR,
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    Text,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class EnrollmentFeeTerm(Base):
    __tablename__ = "enrollment_fee_terms"
    __table_args__ = (
        CheckConstraint("agreed_amount > 0", name="ck_fee_terms_amount"),
        CheckConstraint("currency = 'INR'", name="ck_fee_terms_currency"),
        CheckConstraint(
            "effective_to IS NULL OR effective_to > effective_from",
            name="ck_fee_terms_effective_range",
        ),
        CheckConstraint("length(btrim(reason)) > 0", name="ck_fee_terms_reason_not_blank"),
        Index(
            "ux_fee_terms_one_current_per_enrollment",
            "enrollment_id",
            unique=True,
            postgresql_where=text("effective_to IS NULL"),
        ),
        Index("ix_fee_terms_enrollment_history", "enrollment_id", text("effective_from DESC")),
        {"schema": "internship_management"},
    )

    fee_term_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    enrollment_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "internship_management.enrollments.enrollment_id",
            name="fk_fee_terms_enrollments",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    fee_structure_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(
            "internship_management.fee_structures.fee_structure_id",
            name="fk_fee_terms_fee_structures",
            ondelete="RESTRICT",
        ),
    )
    agreed_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(CHAR(3), nullable=False, server_default=text("'INR'"))
    effective_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.transaction_timestamp()
    )
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "internship_management.admins.admin_id",
            name="fk_fee_terms_created_by_admins",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.transaction_timestamp()
    )
