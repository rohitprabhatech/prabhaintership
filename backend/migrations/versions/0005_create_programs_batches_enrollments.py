"""Create internship programs, batches, and enrollment history.

Revision ID: 0005_create_programs_batches_enrollments
Revises: 0004_create_students
Create Date: 2026-10-16
"""

import sqlalchemy as sa
from alembic import op

revision = "0005_create_programs_batches_enrollments"
down_revision = "0004_create_students"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "internship_programs",
        sa.Column("program_id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("program_code", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), server_default=sa.text("'draft'"), nullable=False),
        sa.Column("created_by", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.transaction_timestamp(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.transaction_timestamp(),
            nullable=False,
        ),
        sa.CheckConstraint("length(btrim(program_code)) > 0", name="ck_program_code_not_blank"),
        sa.CheckConstraint("length(btrim(name)) > 0", name="ck_program_name_not_blank"),
        sa.CheckConstraint("status IN ('draft', 'active', 'inactive')", name="ck_program_status"),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["internship_management.admins.admin_id"],
            name="fk_internship_programs_created_by_admins",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("program_code", name="uq_internship_programs_program_code"),
        schema="internship_management",
    )
    op.create_index(
        "ix_programs_status_name",
        "internship_programs",
        ["status", sa.text("lower(name)")],
        schema="internship_management",
    )

    op.create_table(
        "batches",
        sa.Column("batch_id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("program_id", sa.BigInteger(), nullable=False),
        sa.Column("batch_code", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("starts_on", sa.Date(), nullable=False),
        sa.Column("ends_on", sa.Date(), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=True),
        sa.Column("status", sa.Text(), server_default=sa.text("'planned'"), nullable=False),
        sa.Column("created_by", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.transaction_timestamp(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.transaction_timestamp(),
            nullable=False,
        ),
        sa.CheckConstraint("length(btrim(batch_code)) > 0", name="ck_batches_code_not_blank"),
        sa.CheckConstraint("length(btrim(name)) > 0", name="ck_batches_name_not_blank"),
        sa.CheckConstraint("ends_on >= starts_on", name="ck_batches_dates"),
        sa.CheckConstraint("capacity IS NULL OR capacity > 0", name="ck_batches_capacity"),
        sa.CheckConstraint(
            "status IN ('planned', 'active', 'completed', 'cancelled')",
            name="ck_batches_status",
        ),
        sa.ForeignKeyConstraint(
            ["program_id"],
            ["internship_management.internship_programs.program_id"],
            name="fk_batches_programs",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("program_id", "batch_code", name="uq_batches_program_code"),
        sa.UniqueConstraint("batch_id", "program_id", name="uq_batches_id_program"),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["internship_management.admins.admin_id"],
            name="fk_batches_created_by_admins",
            ondelete="RESTRICT",
        ),
        schema="internship_management",
    )
    op.create_index(
        "ix_batches_program_status_dates",
        "batches",
        ["program_id", "status", "starts_on", "ends_on"],
        schema="internship_management",
    )

    op.create_table(
        "enrollments",
        sa.Column("enrollment_id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("enrollment_number", sa.Text(), nullable=False),
        sa.Column("student_id", sa.BigInteger(), nullable=False),
        sa.Column("program_id", sa.BigInteger(), nullable=False),
        sa.Column("batch_id", sa.BigInteger(), nullable=True),
        sa.Column("status", sa.Text(), server_default=sa.text("'active'"), nullable=False),
        sa.Column("starts_on", sa.Date(), nullable=False),
        sa.Column("ends_on", sa.Date(), nullable=True),
        sa.Column("created_by", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.transaction_timestamp(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.transaction_timestamp(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "length(btrim(enrollment_number)) > 0", name="ck_enrollments_number_not_blank"
        ),
        sa.CheckConstraint(
            "status IN ('active', 'completed', 'withdrawn', 'cancelled')",
            name="ck_enrollments_status",
        ),
        sa.CheckConstraint("ends_on IS NULL OR ends_on >= starts_on", name="ck_enrollments_dates"),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["internship_management.students.student_id"],
            name="fk_enrollments_students",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["program_id"],
            ["internship_management.internship_programs.program_id"],
            name="fk_enrollments_programs",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["batch_id", "program_id"],
            [
                "internship_management.batches.batch_id",
                "internship_management.batches.program_id",
            ],
            name="fk_enrollments_batch_program",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["internship_management.admins.admin_id"],
            name="fk_enrollments_created_by_admins",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("enrollment_number", name="uq_enrollments_enrollment_number"),
        sa.UniqueConstraint("enrollment_id", "program_id", name="uq_enrollments_id_program"),
        schema="internship_management",
    )
    op.create_index(
        "ix_enrollments_student_created",
        "enrollments",
        ["student_id", sa.text("created_at DESC")],
        schema="internship_management",
    )
    op.create_index(
        "ix_enrollments_program_status",
        "enrollments",
        ["program_id", "status", "starts_on"],
        schema="internship_management",
    )
    op.create_index(
        "ix_enrollments_batch_status",
        "enrollments",
        ["batch_id", "status"],
        schema="internship_management",
        postgresql_where=sa.text("batch_id IS NOT NULL"),
    )
    op.create_index(
        "ux_enrollments_one_active_tuple",
        "enrollments",
        ["student_id", "program_id", sa.text("COALESCE(batch_id, 0)")],
        unique=True,
        schema="internship_management",
        postgresql_where=sa.text("status = 'active'"),
    )


def downgrade() -> None:
    op.drop_index(
        "ux_enrollments_one_active_tuple",
        table_name="enrollments",
        schema="internship_management",
    )
    op.drop_index(
        "ix_enrollments_batch_status",
        table_name="enrollments",
        schema="internship_management",
    )
    op.drop_index(
        "ix_enrollments_program_status",
        table_name="enrollments",
        schema="internship_management",
    )
    op.drop_index(
        "ix_enrollments_student_created",
        table_name="enrollments",
        schema="internship_management",
    )
    op.drop_table("enrollments", schema="internship_management")
    op.drop_index(
        "ix_batches_program_status_dates",
        table_name="batches",
        schema="internship_management",
    )
    op.drop_table("batches", schema="internship_management")
    op.drop_index(
        "ix_programs_status_name",
        table_name="internship_programs",
        schema="internship_management",
    )
    op.drop_table("internship_programs", schema="internship_management")
