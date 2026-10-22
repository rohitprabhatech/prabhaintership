from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Computed,
    DateTime,
    ForeignKey,
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


class Student(Base):
    __tablename__ = "students"
    __table_args__ = (
        CheckConstraint("length(trim(full_name)) > 0", name="ck_students_name_not_blank"),
        CheckConstraint("status IN ('active', 'archived')", name="ck_students_status"),
        CheckConstraint(
            "(status = 'archived' AND archived_at IS NOT NULL) "
            "OR (status = 'active' AND archived_at IS NULL)",
            name="ck_students_archive_consistency",
        ),
        UniqueConstraint("student_number", name="uq_students_student_number"),
        Index(
            "ux_students_email_lower",
            "email_normalized",
            unique=True,
        ),
        Index("ix_students_name_lower", "name_search_key"),
        Index("ix_students_status_created", "status", text("created_at DESC")),
        {"schema": DATABASE_SCHEMA},
    )

    student_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    student_number: Mapped[str] = mapped_column(String(64), nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str | None] = mapped_column(String(254))
    email_normalized: Mapped[str | None] = mapped_column(
        String(254), Computed("lower(email)", persisted=True)
    )
    phone: Mapped[str | None] = mapped_column(String(64))
    address: Mapped[str | None] = mapped_column(Text)
    city: Mapped[str | None] = mapped_column(String(120))
    state: Mapped[str | None] = mapped_column(String(120))
    postal_code: Mapped[str | None] = mapped_column(String(32))
    institution_name: Mapped[str | None] = mapped_column(String(200))
    course: Mapped[str | None] = mapped_column(String(200))
    internship_domain: Mapped[str | None] = mapped_column(String(120))
    name_search_key: Mapped[str | None] = mapped_column(
        String(200), Computed("lower(full_name)", persisted=True), nullable=True
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default=text("'active'"))
    created_by: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            f"{DATABASE_SCHEMA}.admins.admin_id",
            name="fk_students_created_by_admins",
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
    archived_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    enrollments: Mapped[list["Enrollment"]] = relationship("Enrollment", back_populates="student")