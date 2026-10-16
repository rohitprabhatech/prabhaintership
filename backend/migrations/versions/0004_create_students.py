"""Create the Sprint 3B Student table.

Revision ID: 0004_create_students
Revises: 0003_admin_login_throttles
Create Date: 2026-10-16
"""

import sqlalchemy as sa
from alembic import op

revision = "0004_create_students"
down_revision = "0003_admin_login_throttles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "students",
        sa.Column("student_id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("student_number", sa.Text(), nullable=False),
        sa.Column("full_name", sa.Text(), nullable=False),
        sa.Column("email", sa.Text(), nullable=True),
        sa.Column("phone", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), server_default=sa.text("'active'"), nullable=False),
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
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("length(btrim(full_name)) > 0", name="ck_students_name_not_blank"),
        sa.CheckConstraint("status IN ('active', 'archived')", name="ck_students_status"),
        sa.CheckConstraint(
            "(status = 'archived' AND archived_at IS NOT NULL) "
            "OR (status = 'active' AND archived_at IS NULL)",
            name="ck_students_archive_consistency",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["internship_management.admins.admin_id"],
            name="fk_students_created_by_admins",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("student_id"),
        sa.UniqueConstraint("student_number", name="uq_students_student_number"),
        schema="internship_management",
    )
    op.create_index(
        "ux_students_email_lower",
        "students",
        [sa.text("lower(email)")],
        unique=True,
        schema="internship_management",
        postgresql_where=sa.text("email IS NOT NULL"),
    )
    op.create_index(
        "ix_students_name_lower",
        "students",
        [sa.text("lower(full_name)")],
        schema="internship_management",
    )
    op.create_index(
        "ix_students_status_created",
        "students",
        ["status", sa.text("created_at DESC")],
        schema="internship_management",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_students_status_created", table_name="students", schema="internship_management"
    )
    op.drop_index(
        "ix_students_name_lower", table_name="students", schema="internship_management"
    )
    op.drop_index(
        "ux_students_email_lower", table_name="students", schema="internship_management"
    )
    op.drop_table("students", schema="internship_management")