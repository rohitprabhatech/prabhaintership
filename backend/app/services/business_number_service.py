from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.orm import Session

from app.errors import APIError
from app.models.business_number_counter import BusinessNumberCounter

_IDENTIFIER_FORMATS = {
    "student": ("STU", 6, 999_999),
    "program": ("PRG", 4, 9_999),
    "batch": ("BAT", 4, 9_999),
    "enrollment": ("ENR", 6, 999_999),
    "project": ("PRJ", 4, 9_999),
    "certificate": ("CERT", 6, 999_999),
}


def generate_business_number(session: Session, entity_key: str) -> str:
    calendar_year = datetime.now(UTC).year
    session.execute(
        mysql_insert(BusinessNumberCounter)
        .values(
            entity_key=entity_key,
            calendar_year=calendar_year,
            counter_value=1,
        )
        .on_duplicate_key_update(counter_value=BusinessNumberCounter.counter_value + 1)
    )
    counter_value = session.scalar(
        select(BusinessNumberCounter.counter_value)
        .where(
            BusinessNumberCounter.entity_key == entity_key,
            BusinessNumberCounter.calendar_year == calendar_year,
        )
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if counter_value is None:
        raise APIError(
            503,
            "identifier_generation_failed",
            "A unique identifier could not be generated. Please retry.",
        )
    return format_business_number(entity_key, calendar_year, counter_value)


def format_business_number(entity_key: str, calendar_year: int, counter_value: int) -> str:
    try:
        prefix, width, maximum = _IDENTIFIER_FORMATS[entity_key]
    except KeyError:
        raise ValueError(f"Unsupported business number entity: {entity_key}") from None
    if counter_value > maximum:
        raise APIError(
            503,
            "identifier_capacity_exhausted",
            "The identifier range for this year is exhausted.",
        )
    return f"{prefix}-{calendar_year}-{counter_value:0{width}d}"
