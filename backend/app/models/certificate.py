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


class Certificate(Base):
    __tablename__ = "certificates"
    __table_args__ = (
        CheckConstraint(
            "length(btrim(certificate_number)) > 0", name="ck_certificates_number_not_blank"
        ),
        CheckConstraint(
            "length(btrim(certificate_type)) > 0", name="ck_certificates_type_not_blank"
        ),
        CheckConstraint(
            "replaces_certificate_id IS NULL OR replaces_certificate_id <> certificate_id",
            name="ck_certificates_not_self_replacement",
        ),
        UniqueConstraint("certificate_number", name="uq_certificates_certificate_number"),
        UniqueConstraint("certificate_id", "enrollment_id", name="uq_certificates_id_enrollment"),
        Index(
            "ix_certificates_enrollment_issued",
            "enrollment_id",
            text("issued_at DESC"),
        ),
        Index(
            "ix_certificates_replaces",
            "replaces_certificate_id",
            postgresql_where=text("replaces_certificate_id IS NOT NULL"),
        ),
        {"schema": "internship_management"},
    )

    certificate_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    enrollment_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "internship_management.enrollments.enrollment_id",
            name="fk_certificates_enrollments",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    certificate_number: Mapped[str] = mapped_column(Text, nullable=False)
    certificate_type: Mapped[str] = mapped_column(Text, nullable=False)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    document_uri: Mapped[str | None] = mapped_column(Text)
    replaces_certificate_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(
            "internship_management.certificates.certificate_id",
            name="fk_certificates_replaces",
            ondelete="RESTRICT",
        ),
    )
    issued_by: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "internship_management.admins.admin_id",
            name="fk_certificates_issued_by_admins",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.transaction_timestamp()
    )
