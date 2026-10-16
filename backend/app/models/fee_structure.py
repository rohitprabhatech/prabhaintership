from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CHAR,
    BigInteger,
    Boolean,
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
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class FeeStructure(Base):
    __tablename__ = "fee_structures"
    __table_args__ = (
        UniqueConstraint("program_id", "name", name="uq_fee_structures_program_name"),
        UniqueConstraint("fee_structure_id", "program_id", name="uq_fee_structures_id_program"),
        CheckConstraint("length(btrim(name)) > 0", name="ck_fee_structures_name_not_blank"),
        CheckConstraint("standard_amount > 0", name="ck_fee_structures_amount"),
        CheckConstraint("currency = 'INR'", name="ck_fee_structures_currency"),
        Index("ix_fee_structures_program_active", "program_id", "is_active"),
        {"schema": "internship_management"},
    )

    fee_structure_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    program_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "internship_management.internship_programs.program_id",
            name="fk_fee_structures_programs",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    standard_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(CHAR(3), nullable=False, server_default=text("'INR'"))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    created_by: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "internship_management.admins.admin_id",
            name="fk_fee_structures_created_by_admins",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.transaction_timestamp()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.transaction_timestamp(),
        onupdate=func.transaction_timestamp(),
    )
