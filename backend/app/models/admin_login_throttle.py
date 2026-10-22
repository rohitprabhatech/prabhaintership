from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Index, Integer, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, DATABASE_SCHEMA
from app.db.types import UTCDateTime


class AdminLoginThrottle(Base):
    __tablename__ = "admin_login_throttles"
    __table_args__ = (
        CheckConstraint("failure_count >= 0", name="ck_admin_login_throttles_failure_count"),
        CheckConstraint(
            "client_key_hash REGEXP '^[0-9a-f]{64}$'",
            name="ck_admin_login_throttles_key_hash",
        ),
        Index("ix_admin_login_throttles_updated_at", "updated_at"),
        {"schema": DATABASE_SCHEMA},
    )

    client_key_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    window_started_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, server_default=func.current_timestamp()
    )
    failure_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    blocked_until: Mapped[datetime | None] = mapped_column(UTCDateTime())
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(),
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )