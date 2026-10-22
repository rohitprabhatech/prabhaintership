from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CHAR,
    BigInteger,
    CheckConstraint,
    Computed,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, DATABASE_SCHEMA
from app.db.types import UTCDateTime


class EnrollmentFeeTerm(Base):
    __tablename__ = "enrollment_fee_terms"
    __table_args__ = (
        CheckConstraint("agreed_amount > 0", name="ck_fee_terms_amount"),
        CheckConstraint("currency = 'INR'", name="ck_fee_terms_currency"),
        CheckConstraint(
            "effective_to IS NULL OR effective_to > effective_from",
            name="ck_fee_terms_effective_range",
        ),
        CheckConstraint("length(trim(reason)) > 0", name="ck_fee_terms_reason_not_blank"),
        Index(
            "ux_fee_terms_one_current_per_enrollment",
            "current_enrollment_id",
            unique=True,
        ),
        Index("ix_fee_terms_enrollment_history", "enrollment_id", text("effective_from DESC")),
        {"schema": DATABASE_SCHEMA},
    )

    fee_term_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    enrollment_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            f"{DATABASE_SCHEMA}.enrollments.enrollment_id",
            name="fk_fee_terms_enrollments",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    current_enrollment_id: Mapped[int | None] = mapped_column(
        BigInteger,
        Computed(
            "CASE WHEN effective_to IS NULL THEN enrollment_id ELSE NULL END",
            persisted=True,
        ),
    )
    fee_structure_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(
            f"{DATABASE_SCHEMA}.fee_structures.fee_structure_id",
            name="fk_fee_terms_fee_structures",
            ondelete="RESTRICT",
        ),
    )
    agreed_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(CHAR(3), nullable=False, server_default=text("'INR'"))
    effective_from: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, server_default=func.current_timestamp()
    )
    effective_to: Mapped[datetime | None] = mapped_column(UTCDateTime())
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    created_by: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            f"{DATABASE_SCHEMA}.admins.admin_id",
            name="fk_fee_terms_created_by_admins",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, server_default=func.current_timestamp()
    )
    enrollment: Mapped["Enrollment"] = relationship("Enrollment", back_populates="fee_terms")
