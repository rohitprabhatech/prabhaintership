from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Integer,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


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
        {"schema": "internship_management"},
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
        DateTime(timezone=True), nullable=False, server_default=func.current_timestamp()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))