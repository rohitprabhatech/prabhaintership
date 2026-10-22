from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import DATABASE_SCHEMA, Base
from app.db.types import UTCDateTime


class Certificate(Base):
    __tablename__ = "certificates"
    __table_args__ = (
        CheckConstraint(
            "length(trim(certificate_number)) > 0", name="ck_certificates_number_not_blank"
        ),
        CheckConstraint(
            "length(trim(certificate_type)) > 0", name="ck_certificates_type_not_blank"
        ),
        UniqueConstraint("certificate_number", name="uq_certificates_certificate_number"),
        UniqueConstraint("certificate_id", "enrollment_id", name="uq_certificates_id_enrollment"),
        Index(
            "ix_certificates_enrollment_issued",
            "enrollment_id",
            "issued_at",
        ),
        Index(
            "ix_certificates_replaces",
            "replaces_certificate_id",
        ),
        {"schema": DATABASE_SCHEMA},
    )

    certificate_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    enrollment_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            f"{DATABASE_SCHEMA}.enrollments.enrollment_id",
            name="fk_certificates_enrollments",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    certificate_number: Mapped[str] = mapped_column(String(128), nullable=False)
    certificate_type: Mapped[str] = mapped_column(String(128), nullable=False)
    issued_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    document_uri: Mapped[str | None] = mapped_column(String(2048))
    replaces_certificate_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(
            f"{DATABASE_SCHEMA}.certificates.certificate_id",
            name="fk_certificates_replaces",
            ondelete="RESTRICT",
        ),
    )
    issued_by: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            f"{DATABASE_SCHEMA}.admins.admin_id",
            name="fk_certificates_issued_by_admins",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, server_default=func.current_timestamp()
    )
    enrollment: Mapped["Enrollment"] = relationship("Enrollment", back_populates="certificates")
    events: Mapped[list["CertificateEvent"]] = relationship(
        "CertificateEvent",
        back_populates="certificate",
        foreign_keys="CertificateEvent.certificate_id",
    )
