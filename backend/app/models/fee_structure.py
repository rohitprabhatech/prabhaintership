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
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, DATABASE_SCHEMA
from app.db.types import UTCDateTime


class FeeStructure(Base):
    __tablename__ = "fee_structures"
    __table_args__ = (
        UniqueConstraint("program_id", "name", name="uq_fee_structures_program_name"),
        UniqueConstraint("fee_structure_id", "program_id", name="uq_fee_structures_id_program"),
        CheckConstraint("length(trim(name)) > 0", name="ck_fee_structures_name_not_blank"),
        CheckConstraint("standard_amount > 0", name="ck_fee_structures_amount"),
        CheckConstraint("currency = 'INR'", name="ck_fee_structures_currency"),
        Index("ix_fee_structures_program_active", "program_id", "is_active"),
        {"schema": DATABASE_SCHEMA},
    )

    fee_structure_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    program_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            f"{DATABASE_SCHEMA}.internship_programs.program_id",
            name="fk_fee_structures_programs",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    standard_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(CHAR(3), nullable=False, server_default=text("'INR'"))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    created_by: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            f"{DATABASE_SCHEMA}.admins.admin_id",
            name="fk_fee_structures_created_by_admins",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, server_default=func.current_timestamp()
    )
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(),
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )
