from sqlalchemy import BigInteger, CheckConstraint, SmallInteger, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, DATABASE_SCHEMA


class BusinessNumberCounter(Base):
    __tablename__ = "business_number_counters"
    __table_args__ = (
        CheckConstraint("counter_value > 0", name="ck_business_number_counter_positive"),
        UniqueConstraint("entity_key", "calendar_year", name="uq_business_number_counter_period"),
        {"schema": DATABASE_SCHEMA},
    )

    counter_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    entity_key: Mapped[str] = mapped_column(String(32), nullable=False)
    calendar_year: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    counter_value: Mapped[int] = mapped_column(BigInteger, nullable=False)
