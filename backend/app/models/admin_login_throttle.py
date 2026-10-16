from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Index, Integer, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AdminLoginThrottle(Base):
    __tablename__ = "admin_login_throttles"
    __table_args__ = (
        CheckConstraint("failure_count >= 0", name="ck_admin_login_throttles_failure_count"),
        CheckConstraint(
            "client_key_hash ~ '^[0-9a-f]{64}$'",
            name="ck_admin_login_throttles_key_hash",
        ),
        Index("ix_admin_login_throttles_updated_at", "updated_at"),
        {"schema": "internship_management"},
    )

    client_key_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    window_started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.transaction_timestamp()
    )
    failure_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    blocked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.transaction_timestamp(),
        onupdate=func.transaction_timestamp(),
    )