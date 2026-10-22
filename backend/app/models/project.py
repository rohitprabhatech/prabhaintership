from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, DATABASE_SCHEMA
from app.db.types import UTCDateTime


class Project(Base):
    __tablename__ = "projects"
    __table_args__ = (
        CheckConstraint("length(trim(project_code)) > 0", name="ck_projects_code_not_blank"),
        CheckConstraint("length(trim(name)) > 0", name="ck_projects_name_not_blank"),
        CheckConstraint("status IN ('active', 'archived')", name="ck_projects_status"),
        UniqueConstraint("project_code", name="uq_projects_project_code"),
        {"schema": DATABASE_SCHEMA},
    )

    project_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    project_code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default=text("'active'"))
    created_by: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            f"{DATABASE_SCHEMA}.admins.admin_id",
            name="fk_projects_created_by_admins",
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
    assignments: Mapped[list["ProjectAssignment"]] = relationship(
        "ProjectAssignment", back_populates="project"
    )
