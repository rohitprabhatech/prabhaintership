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
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class InternshipProgram(Base):
    __tablename__ = "internship_programs"
    __table_args__ = (
        CheckConstraint("length(trim(program_code)) > 0", name="ck_program_code_not_blank"),
        CheckConstraint("length(trim(name)) > 0", name="ck_program_name_not_blank"),
        CheckConstraint("status IN ('draft', 'active', 'inactive')", name="ck_program_status"),
        UniqueConstraint("program_code", name="uq_internship_programs_program_code"),
        Index("ix_programs_status_name", "status", "name_search_key"),
        {"schema": "internship_management"},
    )

    program_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    program_code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
        name_search_key: Mapped[str] = mapped_column(
            String(200), Computed("lower(name)", persisted=True)
        )
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'draft'"))
    created_by: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "internship_management.admins.admin_id",
            name="fk_internship_programs_created_by_admins",
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
