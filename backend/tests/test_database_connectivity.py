import pytest
from sqlalchemy import inspect, text
from app.config import get_settings


@pytest.mark.integration
def test_mysql_connectivity_and_admin_migration(pg_engine) -> None:
    with pg_engine.connect() as connection:
        assert connection.scalar(text("SELECT 1")) == 1
        admin_table_exists = inspect(connection).has_table(
            "admins", schema=get_settings().db_name
        )

    assert admin_table_exists is True