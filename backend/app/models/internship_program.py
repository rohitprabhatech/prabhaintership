from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Computed,
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
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, DATABASE_SCHEMA
from app.db.types import UTCDateTime


class InternshipProgram(Base):
    __tablename__ = "internship_programs"
    __table_args__ = (
        CheckConstraint("length(trim(program_code)) > 0", name="ck_program_code_not_blank"),
        CheckConstraint("length(trim(name)) > 0", name="ck_program_name_not_blank"),
        CheckConstraint(
            "duration_months IS NULL OR duration_months > 0",
            name="ck_program_duration_months_positive",
        ),
        CheckConstraint("status IN ('draft', 'active', 'inactive')", name="ck_program_status"),
        UniqueConstraint("program_code", name="uq_internship_programs_program_code"),
        Index("ix_programs_status_name", "status", "name_search_key"),
        {"schema": DATABASE_SCHEMA},
    )

    program_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    program_code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    name_search_key: Mapped[str | None] = mapped_column(
        String(200), Computed("lower(name)", persisted=True), nullable=True
    )
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default=text("'draft'"))
    duration_months: Mapped[int | None] = mapped_column(Integer)
    created_by: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            f"{DATABASE_SCHEMA}.admins.admin_id",
            name="fk_internship_programs_created_by_admins",
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
    batches: Mapped[list["Batch"]] = relationship("Batch", back_populates="program")
    enrollments: Mapped[list["Enrollment"]] = relationship("Enrollment", back_populates="program")
