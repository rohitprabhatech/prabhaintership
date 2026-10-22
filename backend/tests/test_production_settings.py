import pytest
from pydantic import ValidationError

from app.config import Settings


def _production_settings(**overrides) -> Settings:
    values = {
        "app_env": "production",
        "db_host": "db.example.com",
        "db_port": 3306,
        "db_name": "internship_management",
        "db_user": "app",
        "db_password": "unit-test-password",
        "db_ssl_ca": "C:/certs/mysql-ca.pem",
        "jwt_secret_key": "unit-test-only-random-secret-value-not-for-production",
        "cors_origins": ["https://admin.example.com"],
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_production_requires_https_cors_origins() -> None:
    with pytest.raises(ValidationError, match="Production CORS origins must use HTTPS"):
        _production_settings(cors_origins=["http://admin.example.com"])


def test_production_requires_mysql_tls_ca() -> None:
    with pytest.raises(ValidationError, match="DB_SSL_CA is required"):
        _production_settings(db_ssl_ca=None)


def test_cors_origin_must_not_include_a_path() -> None:
    with pytest.raises(ValidationError, match="without paths or fragments"):
        _production_settings(cors_origins=["https://admin.example.com/portal"])


def test_production_accepts_https_origin_and_mysql_tls() -> None:
    settings = _production_settings()

    assert settings.app_env == "production"
    assert str(settings.cors_origins[0]).startswith("https://admin.example.com")
    assert settings.database_url.drivername == "mysql+pymysql"
    assert settings.database_connect_args["ssl"]["check_hostname"] is True


def test_production_api_settings_do_not_require_operator_database_urls() -> None:
    settings = _production_settings()

    assert settings.database_url.drivername == "mysql+pymysql"


def test_production_migration_requires_migration_database_url() -> None:
    from app.config import MigrationSettings, resolve_migration_database_url

    settings = MigrationSettings(
        _env_file=None,
        app_env="production",
        db_host="db.example.com",
        db_port=3306,
        db_name="internship_management",
        db_user="app",
        db_password="unit-test-password",
    )

    with pytest.raises(ValueError, match="Separate MIGRATION_DB_\* settings are required"):
        resolve_migration_database_url(None, settings)


def test_alembic_explicit_url_overrides_runtime_database_url() -> None:
    from app.config import MigrationSettings, resolve_migration_database_url

    settings = MigrationSettings(
        app_env="test",
        db_host="localhost",
        db_port=3306,
        db_name="runtime",
        db_user="runtime",
        db_password="unit-test-password",
        _env_file=None,
    )
    explicit_test_url = "mysql+pymysql://test:secret@localhost/test_database"

    assert resolve_migration_database_url(explicit_test_url, settings) == explicit_test_url
