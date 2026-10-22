"""Create the Sprint 2 Admin identity table.

Revision ID: 0001_create_admins
Revises:
Create Date: 2026-10-16
"""

from alembic import op
import sqlalchemy as sa
from app.config import MigrationSettings


revision = "0001_create_admins"
down_revision = None
branch_labels = None
depends_on = None
SCHEMA = MigrationSettings().db_name


def upgrade() -> None:
    op.create_table(
        "admins",
        sa.Column("admin_id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("username", sa.String(length=128), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=True),
        sa.Column("email_normalized", sa.String(length=254), sa.Computed("lower(email)", persisted=True)),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
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
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("username = lower(username)", name="ck_admins_username_normalized"),
        sa.CheckConstraint("length(trim(username)) > 0", name="ck_admins_username_not_blank"),
        sa.CheckConstraint(
            "length(trim(password_hash)) > 0", name="ck_admins_password_hash_not_blank"
        ),
        sa.UniqueConstraint("username", name="uq_admins_username"),
        schema=SCHEMA,
    )
    op.create_index(
        "ux_admins_email_lower",
        "admins",
        ["email_normalized"],
        unique=True,
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_index(
        "ux_admins_email_lower",
        table_name="admins",
        schema=SCHEMA,
    )
    op.drop_table("admins", schema=SCHEMA)