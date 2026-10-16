from functools import lru_cache
from typing import Literal

from pydantic import AnyHttpUrl, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL, make_url


def _mysql_url(host: str, port: int, database: str, username: str, password: str) -> URL:
    return URL.create(
        "mysql+pymysql",
        username=username,
        password=password,
        host=host,
        port=port,
        database=database,
    )


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "Prabha Internship Management API"
    app_env: Literal["development", "test", "staging", "production"] = "development"
    db_host: str = "localhost"
    db_port: int = Field(default=3306, ge=1, le=65535)
    db_name: str
    db_user: str
    db_password: SecretStr
    db_ssl_ca: str | None = None
    jwt_secret_key: SecretStr
    jwt_issuer: str = "prabhatech-internship-api"
    jwt_audience: str = "prabhatech-internship-admin"
    access_token_expire_minutes: int = 15
    cors_origins: list[AnyHttpUrl] = Field(default_factory=list)
    auth_rate_limit_attempts: int = 5
    auth_rate_limit_window_seconds: int = 60
    auth_rate_limit_block_seconds: int = 300

    @property
    def database_url(self) -> URL:
        return _mysql_url(
            self.db_host,
            self.db_port,
            self.db_name,
            self.db_user,
            self.db_password.get_secret_value(),
        )

    @property
    def database_connect_args(self) -> dict:
        if not self.db_ssl_ca:
            return {}
        return {"ssl": {"ca": self.db_ssl_ca, "check_hostname": True}}

    @field_validator("jwt_secret_key")
    @classmethod
    def validate_jwt_secret(cls, value: SecretStr) -> SecretStr:
        secret = value.get_secret_value()
        if len(secret) < 32 or "REPLACE_WITH" in secret or "CHANGE_ME" in secret:
            raise ValueError("JWT_SECRET_KEY must be a unique secret of at least 32 characters")
        return value

    @field_validator("access_token_expire_minutes")
    @classmethod
    def validate_token_lifetime(cls, value: int) -> int:
        if not 1 <= value <= 60:
            raise ValueError("ACCESS_TOKEN_EXPIRE_MINUTES must be between 1 and 60")
        return value

    @field_validator(
        "auth_rate_limit_attempts",
        "auth_rate_limit_window_seconds",
        "auth_rate_limit_block_seconds",
    )
    @classmethod
    def validate_positive_rate_limit(cls, value: int) -> int:
        if value < 1:
            raise ValueError("Authentication rate-limit values must be positive")
        return value

    @field_validator("cors_origins")
    @classmethod
    def validate_origin_shape(cls, value: list[AnyHttpUrl]) -> list[AnyHttpUrl]:
        if any(origin.path not in ("", "/") or origin.query or origin.fragment for origin in value):
            raise ValueError("CORS_ORIGINS entries must be origins without paths or fragments")
        return value

    @model_validator(mode="after")
    def validate_production_origins(self) -> "Settings":
        if self.app_env == "production":
            if not self.cors_origins:
                raise ValueError("CORS_ORIGINS must explicitly list trusted origins in production")
            if any(origin.scheme != "https" for origin in self.cors_origins):
                raise ValueError("Production CORS origins must use HTTPS")
            if not self.db_ssl_ca:
                raise ValueError("DB_SSL_CA is required for a production MySQL TLS connection")
        return self


class MigrationSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_env: Literal["development", "test", "staging", "production"] = "development"
    migration_database_url: SecretStr | None = None
    db_host: str = "localhost"
    db_port: int = Field(default=3306, ge=1, le=65535)
    db_name: str
    db_user: str
    db_password: SecretStr
    migration_db_host: str | None = None
    migration_db_port: int | None = Field(default=None, ge=1, le=65535)
    migration_db_name: str | None = None
    migration_db_user: str | None = None
    migration_db_password: SecretStr | None = None

    @field_validator("migration_database_url")
    @classmethod
    def validate_migration_url(cls, value: SecretStr | None) -> SecretStr | None:
        if value is not None and make_url(value.get_secret_value()).drivername != "mysql+pymysql":
            raise ValueError("MIGRATION_DATABASE_URL must use mysql+pymysql")
        return value

    @property
    def database_url(self) -> URL:
        overrides = (
            self.migration_db_host,
            self.migration_db_port,
            self.migration_db_name,
            self.migration_db_user,
            self.migration_db_password,
        )
        if any(value is not None for value in overrides):
            if not all(value is not None for value in overrides):
                raise ValueError("All MIGRATION_DB_* settings must be provided together")
            return _mysql_url(
                self.migration_db_host,
                self.migration_db_port,
                self.migration_db_name,
                self.migration_db_user,
                self.migration_db_password.get_secret_value(),
            )
        if self.app_env == "production":
            raise ValueError("Separate MIGRATION_DB_* settings are required in production")
        return _mysql_url(
            self.db_host,
            self.db_port,
            self.db_name,
            self.db_user,
            self.db_password.get_secret_value(),
        )


class AdminProvisioningSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_env: Literal["development", "test", "staging", "production"] = "development"
    db_host: str = "localhost"
    db_port: int = Field(default=3306, ge=1, le=65535)
    db_name: str
    db_user: str
    db_password: SecretStr
    admin_provisioning_db_host: str | None = None
    admin_provisioning_db_port: int | None = Field(default=None, ge=1, le=65535)
    admin_provisioning_db_name: str | None = None
    admin_provisioning_db_user: str | None = None
    admin_provisioning_db_password: SecretStr | None = None

    @model_validator(mode="after")
    def validate_provisioner(self) -> "AdminProvisioningSettings":
        values = (
            self.admin_provisioning_db_host,
            self.admin_provisioning_db_port,
            self.admin_provisioning_db_name,
            self.admin_provisioning_db_user,
            self.admin_provisioning_db_password,
        )
        if any(value is not None for value in values) and not all(
            value is not None for value in values
        ):
            raise ValueError("All ADMIN_PROVISIONING_DB_* settings must be provided together")
        if self.app_env == "production" and not all(value is not None for value in values):
            raise ValueError("Separate ADMIN_PROVISIONING_DB_* settings are required in production")
        return self

    @property
    def database_url(self) -> URL:
        host = self.admin_provisioning_db_host or self.db_host
        port = self.admin_provisioning_db_port or self.db_port
        database = self.admin_provisioning_db_name or self.db_name
        username = self.admin_provisioning_db_user or self.db_user
        password = self.admin_provisioning_db_password or self.db_password
        return _mysql_url(host, port, database, username, password.get_secret_value())


@lru_cache
def get_settings() -> Settings:
    return Settings()


@lru_cache
def get_admin_provisioning_settings() -> AdminProvisioningSettings:
    return AdminProvisioningSettings()


def resolve_migration_database_url(
    configured_url: str | None, settings: MigrationSettings | None = None
) -> str:
    if configured_url and configured_url.strip():
        return configured_url
    migration_settings = settings or MigrationSettings()
    if migration_settings.migration_database_url is not None:
        return migration_settings.migration_database_url.get_secret_value()
    return migration_settings.database_url.render_as_string(hide_password=False)
