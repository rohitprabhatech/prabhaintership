from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Computed,
    DateTime,
    Integer,
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


class Admin(Base):
    __tablename__ = "admins"
    __table_args__ = (
        CheckConstraint("username = lower(username)", name="ck_admins_username_normalized"),
        CheckConstraint("length(trim(username)) > 0", name="ck_admins_username_not_blank"),
        CheckConstraint("length(trim(password_hash)) > 0", name="ck_admins_password_hash_not_blank"),
        CheckConstraint("auth_version >= 0", name="ck_admins_auth_version_nonnegative"),
        UniqueConstraint("username", name="uq_admins_username"),
        Index(
            "ux_admins_email_lower",
            "email_normalized",
            unique=True,
        ),
        {"schema": DATABASE_SCHEMA},
    )

    admin_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(128), nullable=False)
    email: Mapped[str | None] = mapped_column(String(254))
    email_normalized: Mapped[str | None] = mapped_column(
        String(254), Computed("lower(email)", persisted=True)
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    auth_version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, server_default=func.current_timestamp()
    )
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(),
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )
    last_login_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    students_created: Mapped[list["Student"]] = relationship(
        "Student", foreign_keys="Student.created_by"
    )
    programs_created: Mapped[list["InternshipProgram"]] = relationship(
        "InternshipProgram", foreign_keys="InternshipProgram.created_by"
    )
    batches_created: Mapped[list["Batch"]] = relationship(
        "Batch", foreign_keys="Batch.created_by"
    )
    enrollments_created: Mapped[list["Enrollment"]] = relationship(
        "Enrollment", foreign_keys="Enrollment.created_by"
    )
    fee_structures_created: Mapped[list["FeeStructure"]] = relationship(
        "FeeStructure", foreign_keys="FeeStructure.created_by"
    )
    fee_terms_created: Mapped[list["EnrollmentFeeTerm"]] = relationship(
        "EnrollmentFeeTerm", foreign_keys="EnrollmentFeeTerm.created_by"
    )
    fee_adjustments_approved: Mapped[list["FeeAdjustment"]] = relationship(
        "FeeAdjustment", foreign_keys="FeeAdjustment.approved_by"
    )
    payments_recorded: Mapped[list["Payment"]] = relationship(
        "Payment", foreign_keys="Payment.recorded_by"
    )
    payment_adjustments_recorded: Mapped[list["PaymentAdjustment"]] = relationship(
        "PaymentAdjustment", foreign_keys="PaymentAdjustment.recorded_by"
    )
    projects_created: Mapped[list["Project"]] = relationship(
        "Project", foreign_keys="Project.created_by"
    )
    project_assignments_made: Mapped[list["ProjectAssignment"]] = relationship(
        "ProjectAssignment", foreign_keys="ProjectAssignment.assigned_by"
    )
    certificates_issued: Mapped[list["Certificate"]] = relationship(
        "Certificate", foreign_keys="Certificate.issued_by"
    )
    certificate_events_recorded: Mapped[list["CertificateEvent"]] = relationship(
        "CertificateEvent", foreign_keys="CertificateEvent.recorded_by"
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship(
        "AuditLog", foreign_keys="AuditLog.actor_admin_id", back_populates="actor_admin"
    )