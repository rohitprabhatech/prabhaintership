from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Batch(Base):
    __tablename__ = "batches"
    __table_args__ = (
        UniqueConstraint("program_id", "batch_code", name="uq_batches_program_code"),
        UniqueConstraint("batch_id", "program_id", name="uq_batches_id_program"),
        CheckConstraint("length(trim(batch_code)) > 0", name="ck_batches_code_not_blank"),
        CheckConstraint("length(trim(name)) > 0", name="ck_batches_name_not_blank"),
        CheckConstraint("ends_on >= starts_on", name="ck_batches_dates"),
        CheckConstraint("capacity IS NULL OR capacity > 0", name="ck_batches_capacity"),
        CheckConstraint(
            "status IN ('planned', 'active', 'completed', 'cancelled')",
            name="ck_batches_status",
        ),
        Index("ix_batches_program_status_dates", "program_id", "status", "starts_on", "ends_on"),
        {"schema": "internship_management"},
    )

    batch_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    program_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "internship_management.internship_programs.program_id",
            name="fk_batches_programs",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    batch_code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    starts_on: Mapped[date] = mapped_column(Date, nullable=False)
    ends_on: Mapped[date] = mapped_column(Date, nullable=False)
    capacity: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'planned'"))
    created_by: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "internship_management.admins.admin_id",
            name="fk_batches_created_by_admins",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.current_timestamp()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )
