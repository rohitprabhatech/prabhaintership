from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
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


class ProjectAssignment(Base):
    __tablename__ = "project_assignments"
    __table_args__ = (
        UniqueConstraint(
            "project_id", "enrollment_id", name="uq_project_assignments_project_enrollment"
        ),
        CheckConstraint(
            "status IN ('assigned', 'in_progress', 'completed', 'cancelled')",
            name="ck_project_assignments_status",
        ),
        CheckConstraint(
            "completed_at IS NULL OR completed_at >= assigned_at",
            name="ck_project_assignments_completion",
        ),
        Index("ix_project_assignments_enrollment_status", "enrollment_id", "status"),
        Index("ix_project_assignments_project_status", "project_id", "status"),
        {"schema": DATABASE_SCHEMA},
    )

    project_assignment_id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    project_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            f"{DATABASE_SCHEMA}.projects.project_id",
            name="fk_project_assignments_projects",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    enrollment_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            f"{DATABASE_SCHEMA}.enrollments.enrollment_id",
            name="fk_project_assignments_enrollments",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default=text("'assigned'"))
    assigned_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, server_default=func.current_timestamp()
    )
    completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    assigned_by: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            f"{DATABASE_SCHEMA}.admins.admin_id",
            name="fk_project_assignments_assigned_by_admins",
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
    project: Mapped["Project"] = relationship("Project", back_populates="assignments")
    enrollment: Mapped["Enrollment"] = relationship("Enrollment", back_populates="project_assignments")
