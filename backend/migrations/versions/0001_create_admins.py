"""Create the Sprint 2 Admin identity table.

Revision ID: 0001_create_admins
Revises:
Create Date: 2026-10-16
"""

from alembic import op
import sqlalchemy as sa


revision = "0001_create_admins"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS internship_management")
    op.create_table(
        "admins",
        sa.Column("admin_id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("username", sa.Text(), nullable=False),
        sa.Column("email", sa.Text(), nullable=True),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
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
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("username = lower(username)", name="ck_admins_username_normalized"),
        sa.CheckConstraint("length(btrim(username)) > 0", name="ck_admins_username_not_blank"),
        sa.CheckConstraint(
            "length(btrim(password_hash)) > 0", name="ck_admins_password_hash_not_blank"
        ),
        sa.UniqueConstraint("username", name="uq_admins_username"),
        schema="internship_management",
    )
    op.create_index(
        "ux_admins_email_lower",
        "admins",
        [sa.text("lower(email)")],
        unique=True,
        schema="internship_management",
        postgresql_where=sa.text("email IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "ux_admins_email_lower",
        table_name="admins",
        schema="internship_management",
    )
    op.drop_table("admins", schema="internship_management")