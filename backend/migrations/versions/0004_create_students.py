"""Create the Sprint 3B Student table.

Revision ID: 0004_create_students
Revises: 0003_admin_login_throttles
Create Date: 2026-10-16
"""

import sqlalchemy as sa
from alembic import op
from app.config import MigrationSettings

revision = "0004_create_students"
down_revision = "0003_admin_login_throttles"
branch_labels = None
depends_on = None
SCHEMA = MigrationSettings().db_name


def upgrade() -> None:
    op.create_table(
        "students",
        sa.Column("student_id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("student_number", sa.String(length=64), nullable=False),
        sa.Column("full_name", sa.String(length=200), nullable=False),
        sa.Column("name_search_key", sa.String(length=200), sa.Computed("lower(full_name)", persisted=True)),
        sa.Column("email", sa.String(length=254), nullable=True),
        sa.Column("email_normalized", sa.String(length=254), sa.Computed("lower(email)", persisted=True)),
        sa.Column("phone", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=16), server_default=sa.text("'active'"), nullable=False),
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
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("length(trim(full_name)) > 0", name="ck_students_name_not_blank"),
        sa.CheckConstraint("status IN ('active', 'archived')", name="ck_students_status"),
        sa.CheckConstraint(
            "(status = 'archived' AND archived_at IS NOT NULL) "
            "OR (status = 'active' AND archived_at IS NULL)",
            name="ck_students_archive_consistency",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            [f"{SCHEMA}.admins.admin_id"],
            name="fk_students_created_by_admins",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("student_id"),
        sa.UniqueConstraint("student_number", name="uq_students_student_number"),
        schema=SCHEMA,
    )
    op.create_index(
            "ux_students_email_lower",
            "students",
            ["email_normalized"],
        unique=True,
        schema=SCHEMA,
    )
    op.create_index(
        "ix_students_name_lower",
        "students",
        ["name_search_key"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_students_status_created",
        "students",
        ["status", "created_at"],
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_students_status_created", table_name="students", schema=SCHEMA
    )
    op.drop_index(
        "ix_students_name_lower", table_name="students", schema=SCHEMA
    )
    op.drop_index(
        "ux_students_email_lower", table_name="students", schema=SCHEMA
    )
    op.drop_table("students", schema=SCHEMA)