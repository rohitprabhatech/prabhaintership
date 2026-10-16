from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


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
        {"schema": "internship_management"},
    )

    project_assignment_id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    project_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "internship_management.projects.project_id",
            name="fk_project_assignments_projects",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    enrollment_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "internship_management.enrollments.enrollment_id",
            name="fk_project_assignments_enrollments",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'assigned'"))
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.transaction_timestamp()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    assigned_by: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "internship_management.admins.admin_id",
            name="fk_project_assignments_assigned_by_admins",
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
