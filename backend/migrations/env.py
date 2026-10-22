from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.config import MigrationSettings, resolve_migration_database_url
from app.db.base import Base
from app.models import Admin  # noqa: F401

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

configured_url = config.get_main_option("sqlalchemy.url")
migration_settings = MigrationSettings()
migration_url = resolve_migration_database_url(configured_url, migration_settings)
database_schema = migration_settings.migration_db_name or migration_settings.db_name
config.set_main_option("sqlalchemy.url", migration_url.replace("%", "%%"))
target_metadata = Base.metadata


def _foreign_key_matches_across_default_schema(foreign_key, other) -> bool:
    if foreign_key.table.name != other.table.name:
        return False

    def signature(constraint):
        return (
            constraint.name,
            tuple(column.name for column in constraint.columns),
            tuple(
                (element.column.table.name, element.column.name)
                for element in constraint.elements
            ),
            constraint.ondelete,
            constraint.onupdate,
            constraint.deferrable,
            constraint.initially,
            constraint.match,
        )

    if signature(foreign_key) != signature(other):
        return False
    schemas = [
        foreign_key.table.schema,
        other.table.schema,
        *(element.column.table.schema for element in foreign_key.elements),
        *(element.column.table.schema for element in other.elements),
    ]
    return all(schema in (None, database_schema) for schema in schemas)


def include_object(object_, name, type_, reflected, compare_to):
    if type_ == "table" and name == "alembic_version":
        return False
    if (
        type_ == "foreign_key_constraint"
        and compare_to is not None
        and _foreign_key_matches_across_default_schema(object_, compare_to)
    ):
        return False
    return True


def include_name(name, type_, parent_names):
    if type_ == "schema":
        return name in (None, database_schema)
    if type_ == "table":
        return (
            parent_names.get("schema_name") in (None, database_schema)
            and name != "alembic_version"
        )
    return True


def run_migrations_offline() -> None:
    context.configure(
        url=migration_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_schemas=True,
        include_object=include_object,
        version_table_schema=database_schema,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args=migration_settings.database_connect_args,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_schemas=True,
            include_name=include_name,
            include_object=include_object,
            version_table_schema=database_schema,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
