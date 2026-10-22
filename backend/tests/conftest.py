import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, delete, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker
from starlette.testclient import TestClient


os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "3306")
os.environ.setdefault("DB_NAME", "internship_management_test")
os.environ.setdefault("DB_USER", "test")
os.environ.setdefault("DB_PASSWORD", "test-only-password")
os.environ.setdefault("JWT_SECRET_KEY", "test-only-secret-value-not-for-production-0123456789")
os.environ.setdefault("CORS_ORIGINS", "[]")


@pytest.fixture(scope="session")
def pg_engine():
    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("Set TEST_DATABASE_URL to an isolated MySQL test database")
    test_url = make_url(database_url)
    configured_database = os.getenv("DB_NAME")
    if test_url.drivername != "mysql+pymysql":
        pytest.fail("TEST_DATABASE_URL must use the mysql+pymysql driver")
    if test_url.database != configured_database or test_url.database == "internship_management":
        pytest.fail("TEST_DATABASE_URL and DB_NAME must point to a separate *_test database")

    engine = create_engine(
        database_url,
        pool_pre_ping=True,
        isolation_level="READ COMMITTED",
        connect_args={"init_command": "SET time_zone = '+00:00'"},
    )
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT 1")) == 1

    backend_root = Path(__file__).resolve().parents[1]
    alembic_config = Config(str(backend_root / "alembic.ini"))
    alembic_config.set_main_option("script_location", str(backend_root / "migrations"))
    alembic_config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    command.upgrade(alembic_config, "head")

    yield engine
    engine.dispose()


@pytest.fixture
def db_session(pg_engine):
    session_factory = sessionmaker(bind=pg_engine, autoflush=False, expire_on_commit=False)
    with session_factory() as session:
        yield session


@pytest.fixture
def api_client(pg_engine):
    from app.api.deps import get_db
    from app.main import app
    from app.models.admin_login_throttle import AdminLoginThrottle

    session_factory = sessionmaker(bind=pg_engine, autoflush=False, expire_on_commit=False)
    with session_factory() as session:
        session.execute(delete(AdminLoginThrottle))
        session.commit()

    def override_get_db():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()