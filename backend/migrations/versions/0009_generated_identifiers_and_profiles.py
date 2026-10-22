"""Add transactional business-number counters and extended profiles.

Revision ID: 0009
Revises: 0008
"""

from alembic import op
from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    inspect,
    text,
)

from app.config import MigrationSettings

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None
SCHEMA = MigrationSettings().db_name


def _count(statement: str) -> int:
    return op.get_bind().execute(text(statement)).scalar_one()


def _inspector():
    return inspect(op.get_bind())


def _has_column(table: str, column: str) -> bool:
    return column in {item["name"] for item in _inspector().get_columns(table, schema=SCHEMA)}


def _has_named_object(table: str, collection: str, name: str) -> bool:
    inspector = _inspector()
    objects = getattr(inspector, f"get_{collection}")(table, schema=SCHEMA)
    return any(item.get("name") == name for item in objects)


def _preflight() -> None:
    missing_batch_links = _count(
        f"SELECT COUNT(*) FROM `{SCHEMA}`.`enrollments` WHERE `batch_id` IS NULL"
    )
    if missing_batch_links:
        raise RuntimeError(
            f"Migration 0009 stopped before changing the schema: {missing_batch_links} "
            "enrollment(s) have no batch. Assign each to the correct batch after owner review."
        )

    invalid_batch_links = _count(
        f"""SELECT COUNT(*)
              FROM `{SCHEMA}`.`enrollments` AS e
              LEFT JOIN `{SCHEMA}`.`batches` AS b ON b.batch_id = e.batch_id
             WHERE b.batch_id IS NULL OR b.program_id <> e.program_id"""
    )
    if invalid_batch_links:
        raise RuntimeError(
            f"Migration 0009 stopped before changing the schema: {invalid_batch_links} "
            "enrollment(s) do not reference a batch belonging to their program."
        )

    duplicate_batch_codes = _count(
        f"""SELECT COUNT(*) FROM (
                SELECT batch_code FROM `{SCHEMA}`.`batches`
                 GROUP BY batch_code HAVING COUNT(*) > 1
            ) AS duplicate_codes"""
    )
    if duplicate_batch_codes:
        raise RuntimeError(
            f"Migration 0009 stopped before changing the schema: {duplicate_batch_codes} "
            "batch code(s) are duplicated across programs. Resolve them without overwriting "
            "valid historical identifiers, then retry."
        )


def _seed_counter(entity: str, table: str, column: str, prefix: str, width: int) -> None:
    prefix_length = len(prefix)
    number_start = prefix_length + 7
    statement = f"""
        INSERT INTO `{SCHEMA}`.`business_number_counters`
            (`entity_key`, `calendar_year`, `counter_value`)
        SELECT '{entity}', CAST(SUBSTRING(UPPER(`{column}`), {prefix_length + 2}, 4) AS UNSIGNED),
               MAX(CAST(SUBSTRING(UPPER(`{column}`), {number_start}) AS UNSIGNED))
          FROM `{SCHEMA}`.`{table}`
         WHERE UPPER(`{column}`) REGEXP '^{prefix}-[0-9]{{4}}-[0-9]{{{width}}}$'
         GROUP BY CAST(SUBSTRING(UPPER(`{column}`), {prefix_length + 2}, 4) AS UNSIGNED)
        ON DUPLICATE KEY UPDATE
            `counter_value` = GREATEST(`counter_value`, VALUES(`counter_value`))
    """
    op.get_bind().execute(text(statement))


def upgrade() -> None:
    _preflight()

    if not _inspector().has_table("business_number_counters", schema=SCHEMA):
        op.create_table(
            "business_number_counters",
            Column("counter_id", BigInteger, primary_key=True, autoincrement=True),
            Column("entity_key", String(32), nullable=False),
            Column("calendar_year", SmallInteger, nullable=False),
            Column("counter_value", BigInteger, nullable=False),
            CheckConstraint("counter_value > 0", name="ck_business_number_counter_positive"),
            UniqueConstraint(
                "entity_key", "calendar_year", name="uq_business_number_counter_period"
            ),
            schema=SCHEMA,
        )

    for name, column_type in (
        ("address", Text()),
        ("city", String(120)),
        ("state", String(120)),
        ("postal_code", String(32)),
        ("institution_name", String(200)),
        ("course", String(200)),
        ("internship_domain", String(120)),
    ):
        if not _has_column("students", name):
            op.add_column("students", Column(name, column_type), schema=SCHEMA)

    if not _has_column("internship_programs", "duration_months"):
        op.add_column(
            "internship_programs",
            Column("duration_months", Integer()),
            schema=SCHEMA,
        )
    if not _has_named_object(
        "internship_programs", "check_constraints", "ck_program_duration_months_positive"
    ):
        op.create_check_constraint(
            "ck_program_duration_months_positive",
            "internship_programs",
            "duration_months IS NULL OR duration_months > 0",
            schema=SCHEMA,
        )

    if not _has_named_object("batches", "unique_constraints", "uq_batches_batch_code"):
        op.create_unique_constraint(
            "uq_batches_batch_code", "batches", ["batch_code"], schema=SCHEMA
        )
    if _has_named_object("batches", "unique_constraints", "uq_batches_program_code"):
        op.drop_constraint("uq_batches_program_code", "batches", type_="unique", schema=SCHEMA)

    batch_id = next(
        column
        for column in _inspector().get_columns("enrollments", schema=SCHEMA)
        if column["name"] == "batch_id"
    )
    has_batch_program_fk = _has_named_object(
        "enrollments", "foreign_keys", "fk_enrollments_batch_program"
    )
    if batch_id["nullable"]:
        if has_batch_program_fk:
            op.drop_constraint(
                "fk_enrollments_batch_program",
                "enrollments",
                type_="foreignkey",
                schema=SCHEMA,
            )
        op.alter_column(
            "enrollments",
            "batch_id",
            existing_type=BigInteger,
            nullable=False,
            schema=SCHEMA,
        )
        has_batch_program_fk = False
    if not has_batch_program_fk:
        op.create_foreign_key(
            "fk_enrollments_batch_program",
            "enrollments",
            "batches",
            ["batch_id", "program_id"],
            ["batch_id", "program_id"],
            source_schema=SCHEMA,
            referent_schema=SCHEMA,
            ondelete="RESTRICT",
        )

    for entity, table, column, prefix, width in (
        ("student", "students", "student_number", "STU", 6),
        ("program", "internship_programs", "program_code", "PRG", 4),
        ("batch", "batches", "batch_code", "BAT", 4),
        ("enrollment", "enrollments", "enrollment_number", "ENR", 6),
        ("project", "projects", "project_code", "PRJ", 4),
        ("certificate", "certificates", "certificate_number", "CERT", 6),
    ):
        _seed_counter(entity, table, column, prefix, width)


def downgrade() -> None:
    raise RuntimeError(
        "Migration 0009 is forward-only. Restore a reviewed backup to reverse it; "
        "automatic downgrade could discard profile data and weaken identifiers."
    )
