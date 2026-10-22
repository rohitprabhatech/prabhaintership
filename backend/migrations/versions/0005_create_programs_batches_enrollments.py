"""Create internship programs, batches, and enrollment history.

Revision ID: 0005_create_programs_batches_enrollments
Revises: 0004_create_students
Create Date: 2026-10-16
"""

import sqlalchemy as sa
from alembic import op
from app.config import MigrationSettings

revision = "0005"
down_revision = "0004_create_students"
branch_labels = None
depends_on = None
SCHEMA = MigrationSettings().db_name


def upgrade() -> None:
    op.create_table(
        "internship_programs",
        sa.Column("program_id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("program_code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("name_search_key", sa.String(length=200), sa.Computed("lower(name)", persisted=True)),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=16), server_default=sa.text("'draft'"), nullable=False),
        sa.Column("created_by", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.current_timestamp(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.current_timestamp(),
            nullable=False,
        ),
        sa.CheckConstraint("length(trim(program_code)) > 0", name="ck_program_code_not_blank"),
        sa.CheckConstraint("length(trim(name)) > 0", name="ck_program_name_not_blank"),
        sa.CheckConstraint("status IN ('draft', 'active', 'inactive')", name="ck_program_status"),
        sa.ForeignKeyConstraint(
            ["created_by"],
            [f"{SCHEMA}.admins.admin_id"],
            name="fk_internship_programs_created_by_admins",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("program_code", name="uq_internship_programs_program_code"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_programs_status_name",
        "internship_programs",
        ["status", "name_search_key"],
        schema=SCHEMA,
    )

    op.create_table(
        "batches",
        sa.Column("batch_id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("program_id", sa.BigInteger(), nullable=False),
        sa.Column("batch_code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("starts_on", sa.Date(), nullable=False),
        sa.Column("ends_on", sa.Date(), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=16), server_default=sa.text("'planned'"), nullable=False),
        sa.Column("created_by", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.current_timestamp(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.current_timestamp(),
            nullable=False,
        ),
        sa.CheckConstraint("length(trim(batch_code)) > 0", name="ck_batches_code_not_blank"),
        sa.CheckConstraint("length(trim(name)) > 0", name="ck_batches_name_not_blank"),
        sa.CheckConstraint("ends_on >= starts_on", name="ck_batches_dates"),
        sa.CheckConstraint("capacity IS NULL OR capacity > 0", name="ck_batches_capacity"),
        sa.CheckConstraint(
            "status IN ('planned', 'active', 'completed', 'cancelled')",
            name="ck_batches_status",
        ),
        sa.ForeignKeyConstraint(
            ["program_id"],
            [f"{SCHEMA}.internship_programs.program_id"],
            name="fk_batches_programs",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("program_id", "batch_code", name="uq_batches_program_code"),
        sa.UniqueConstraint("batch_id", "program_id", name="uq_batches_id_program"),
        sa.ForeignKeyConstraint(
            ["created_by"],
            [f"{SCHEMA}.admins.admin_id"],
            name="fk_batches_created_by_admins",
            ondelete="RESTRICT",
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_batches_program_status_dates",
        "batches",
        ["program_id", "status", "starts_on", "ends_on"],
        schema=SCHEMA,
    )

    op.create_table(
        "enrollments",
        sa.Column("enrollment_id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("enrollment_number", sa.String(length=64), nullable=False),
        sa.Column("student_id", sa.BigInteger(), nullable=False),
        sa.Column("program_id", sa.BigInteger(), nullable=False),
        sa.Column("batch_id", sa.BigInteger(), nullable=True),
        sa.Column("status", sa.String(length=16), server_default=sa.text("'active'"), nullable=False),
        sa.Column("active_batch_key", sa.BigInteger(), sa.Computed("CASE WHEN status = 'active' THEN COALESCE(batch_id, 0) ELSE NULL END", persisted=True)),
        sa.Column("starts_on", sa.Date(), nullable=False),
        sa.Column("ends_on", sa.Date(), nullable=True),
        sa.Column("created_by", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.current_timestamp(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.current_timestamp(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "length(trim(enrollment_number)) > 0", name="ck_enrollments_number_not_blank"
        ),
        sa.CheckConstraint(
            "status IN ('active', 'completed', 'withdrawn', 'cancelled')",
            name="ck_enrollments_status",
        ),
        sa.CheckConstraint("ends_on IS NULL OR ends_on >= starts_on", name="ck_enrollments_dates"),
        sa.ForeignKeyConstraint(
            ["student_id"],
            [f"{SCHEMA}.students.student_id"],
            name="fk_enrollments_students",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["program_id"],
            [f"{SCHEMA}.internship_programs.program_id"],
            name="fk_enrollments_programs",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["batch_id", "program_id"],
            [
                f"{SCHEMA}.batches.batch_id",
                f"{SCHEMA}.batches.program_id",
            ],
            name="fk_enrollments_batch_program",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            [f"{SCHEMA}.admins.admin_id"],
            name="fk_enrollments_created_by_admins",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("enrollment_number", name="uq_enrollments_enrollment_number"),
        sa.UniqueConstraint("enrollment_id", "program_id", name="uq_enrollments_id_program"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_enrollments_student_created",
        "enrollments",
        ["student_id", sa.text("created_at DESC")],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_enrollments_program_status",
        "enrollments",
        ["program_id", "status", "starts_on"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_enrollments_batch_status",
        "enrollments",
        ["batch_id", "status"],
        schema=SCHEMA,
    )
    op.create_index(
        "ux_enrollments_one_active_tuple",
        "enrollments",
        ["student_id", "program_id", "active_batch_key"],
        unique=True,
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_index(
        "ux_enrollments_one_active_tuple",
        table_name="enrollments",
        schema=SCHEMA,
    )
    op.drop_index(
        "ix_enrollments_batch_status",
        table_name="enrollments",
        schema=SCHEMA,
    )
    op.drop_index(
        "ix_enrollments_program_status",
        table_name="enrollments",
        schema=SCHEMA,
    )
    op.drop_index(
        "ix_enrollments_student_created",
        table_name="enrollments",
        schema=SCHEMA,
    )
    op.drop_table("enrollments", schema=SCHEMA)
    op.drop_index(
        "ix_batches_program_status_dates",
        table_name="batches",
        schema=SCHEMA,
    )
    op.drop_table("batches", schema=SCHEMA)
    op.drop_index(
        "ix_programs_status_name",
        table_name="internship_programs",
        schema=SCHEMA,
    )
    op.drop_table("internship_programs", schema=SCHEMA)
