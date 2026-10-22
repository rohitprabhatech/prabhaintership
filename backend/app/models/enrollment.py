from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Computed,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, DATABASE_SCHEMA
from app.db.types import UTCDateTime


class Enrollment(Base):
    __tablename__ = "enrollments"
    __table_args__ = (
        ForeignKeyConstraint(
            ["batch_id", "program_id"],
            [
                f"{DATABASE_SCHEMA}.batches.batch_id",
                f"{DATABASE_SCHEMA}.batches.program_id",
            ],
            name="fk_enrollments_batch_program",
            ondelete="RESTRICT",
        ),
        UniqueConstraint("enrollment_number", name="uq_enrollments_enrollment_number"),
        UniqueConstraint("enrollment_id", "program_id", name="uq_enrollments_id_program"),
        CheckConstraint(
            "length(trim(enrollment_number)) > 0", name="ck_enrollments_number_not_blank"
        ),
        CheckConstraint(
            "status IN ('active', 'completed', 'withdrawn', 'cancelled')",
            name="ck_enrollments_status",
        ),
        CheckConstraint("ends_on IS NULL OR ends_on >= starts_on", name="ck_enrollments_dates"),
        Index("ix_enrollments_student_created", "student_id", text("created_at DESC")),
        Index("ix_enrollments_program_status", "program_id", "status", "starts_on"),
        Index(
            "ix_enrollments_batch_status",
            "batch_id",
            "status",
        ),
        Index(
            "ux_enrollments_one_active_tuple",
            "student_id",
            "program_id",
            "active_batch_key",
            unique=True,
        ),
        {"schema": DATABASE_SCHEMA},
    )

    enrollment_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    enrollment_number: Mapped[str] = mapped_column(String(64), nullable=False)
    student_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            f"{DATABASE_SCHEMA}.students.student_id",
            name="fk_enrollments_students",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    program_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            f"{DATABASE_SCHEMA}.internship_programs.program_id",
            name="fk_enrollments_programs",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    batch_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    active_batch_key: Mapped[int | None] = mapped_column(
        BigInteger,
        Computed(
            "CASE WHEN status = 'active' THEN COALESCE(batch_id, 0) ELSE NULL END",
            persisted=True,
        ),
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default=text("'active'"))
    starts_on: Mapped[date] = mapped_column(Date, nullable=False)
    ends_on: Mapped[date | None] = mapped_column(Date)
    created_by: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            f"{DATABASE_SCHEMA}.admins.admin_id",
            name="fk_enrollments_created_by_admins",
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
    student: Mapped["Student"] = relationship("Student", back_populates="enrollments")
    program: Mapped["InternshipProgram"] = relationship("InternshipProgram", back_populates="enrollments")
    batch: Mapped["Batch"] = relationship(
        "Batch",
        primaryjoin=(
            "and_(foreign(Enrollment.batch_id) == Batch.batch_id, "
            "Enrollment.program_id == Batch.program_id)"
        ),
        back_populates="enrollments",
        viewonly=True,
    )
    fee_terms: Mapped[list["EnrollmentFeeTerm"]] = relationship(
        "EnrollmentFeeTerm", back_populates="enrollment"
    )
    payments: Mapped[list["Payment"]] = relationship("Payment", back_populates="enrollment")
    project_assignments: Mapped[list["ProjectAssignment"]] = relationship(
        "ProjectAssignment", back_populates="enrollment"
    )
    certificates: Mapped[list["Certificate"]] = relationship(
        "Certificate", back_populates="enrollment"
    )
