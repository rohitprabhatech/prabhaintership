import pytest
from pydantic import ValidationError

from app.config import Settings


def _production_settings(**overrides) -> Settings:
    values = {
        "app_env": "production",
        "database_url": "postgresql+psycopg://app:secret@db.example.com/app?sslmode=verify-full",
        "jwt_secret_key": "unit-test-only-random-secret-value-not-for-production",
        "cors_origins": ["https://admin.example.com"],
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_production_requires_https_cors_origins() -> None:
    with pytest.raises(ValidationError, match="Production CORS origins must use HTTPS"):
        _production_settings(cors_origins=["http://admin.example.com"])


def test_production_requires_tls_database_url() -> None:
    with pytest.raises(ValidationError, match="DATABASE_URL must set sslmode"):
        _production_settings(database_url="postgresql+psycopg://app:secret@db.example.com/app")


def test_cors_origin_must_not_include_a_path() -> None:
    with pytest.raises(ValidationError, match="without paths or fragments"):
        _production_settings(cors_origins=["https://admin.example.com/portal"])


def test_production_accepts_https_origin_and_verified_tls() -> None:
    settings = _production_settings()

    assert settings.app_env == "production"
    assert str(settings.cors_origins[0]).startswith("https://admin.example.com")


def test_production_api_settings_do_not_require_operator_database_urls() -> None:
    settings = _production_settings()

    assert settings.database_url.get_secret_value().startswith("postgresql+psycopg://app:")


def test_production_migration_requires_migration_database_url() -> None:
    from app.config import MigrationSettings, resolve_migration_database_url

    settings = MigrationSettings(
        _env_file=None,
        app_env="production",
        database_url="postgresql+psycopg://app:secret@db.example.com/app?sslmode=verify-full",
    )

    with pytest.raises(ValueError, match="MIGRATION_DATABASE_URL is required"):
        resolve_migration_database_url(None, settings)


def test_alembic_explicit_url_overrides_runtime_database_url() -> None:
    from app.config import MigrationSettings, resolve_migration_database_url

    settings = MigrationSettings(
        app_env="test",
        database_url="postgresql+psycopg://runtime:secret@localhost/runtime",
        _env_file=None,
    )
    explicit_test_url = "postgresql+psycopg://test:secret@localhost/test_database"

    assert resolve_migration_database_url(explicit_test_url, settings) == explicit_test_url
