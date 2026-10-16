import pytest
from sqlalchemy import text


@pytest.mark.integration
def test_postgresql_connectivity_and_admin_migration(pg_engine) -> None:
    with pg_engine.connect() as connection:
        assert connection.scalar(text("SELECT 1")) == 1
        admin_table_exists = connection.scalar(
            text(
                "SELECT to_regclass('internship_management.admins') IS NOT NULL"
            )
        )

    assert admin_table_exists is True