"""Add per-Admin token invalidation version.

Revision ID: 0002_admin_auth_version
Revises: 0001_create_admins
Create Date: 2026-10-16
"""

from alembic import op
import sqlalchemy as sa
from app.config import MigrationSettings


revision = "0002_admin_auth_version"
down_revision = "0001_create_admins"
branch_labels = None
depends_on = None
SCHEMA = MigrationSettings().db_name


def upgrade() -> None:
    op.add_column(
        "admins",
        sa.Column("auth_version", sa.Integer(), server_default=sa.text("0"), nullable=False),
        schema=SCHEMA,
    )
    op.create_check_constraint(
        "ck_admins_auth_version_nonnegative",
        "admins",
        "auth_version >= 0",
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_admins_auth_version_nonnegative",
        "admins",
        schema=SCHEMA,
        type_="check",
    )
    op.drop_column("admins", "auth_version", schema=SCHEMA)