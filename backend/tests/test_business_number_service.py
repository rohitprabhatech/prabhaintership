from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy.orm import sessionmaker

from app.errors import APIError
from app.services.business_number_service import (
    format_business_number,
    generate_business_number,
)


@pytest.mark.parametrize(
    ("entity_key", "expected"),
    [
        ("student", "STU-2026-000001"),
        ("program", "PRG-2026-0001"),
        ("batch", "BAT-2026-0001"),
        ("enrollment", "ENR-2026-000001"),
        ("project", "PRJ-2026-0001"),
        ("certificate", "CERT-2026-000001"),
    ],
)
def test_business_number_formats(entity_key: str, expected: str) -> None:
    assert format_business_number(entity_key, 2026, 1) == expected


def test_business_number_format_rejects_exhausted_range() -> None:
    with pytest.raises(APIError) as error:
        format_business_number("program", 2026, 10_000)
    assert error.value.code == "identifier_capacity_exhausted"


@pytest.mark.integration
def test_counter_allocations_are_unique_under_concurrency(pg_engine) -> None:
    session_factory = sessionmaker(bind=pg_engine, autoflush=False, expire_on_commit=False)

    def allocate(entity_key: str) -> str:
        with session_factory() as session:
            try:
                value = generate_business_number(session, entity_key)
                session.commit()
                return value
            except Exception:
                session.rollback()
                raise

    for entity_key in ("student", "program", "batch", "enrollment", "project", "certificate"):
        with ThreadPoolExecutor(max_workers=8) as executor:
            values = list(executor.map(lambda _: allocate(entity_key), range(8)))
        assert len(values) == len(set(values))
