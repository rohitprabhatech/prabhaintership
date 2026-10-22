"""Add shared Admin login throttling buckets.

Revision ID: 0003_admin_login_throttles
Revises: 0002_admin_auth_version
Create Date: 2026-10-16
"""

from alembic import op
import sqlalchemy as sa
from app.config import MigrationSettings


revision = "0003_admin_login_throttles"
down_revision = "0002_admin_auth_version"
branch_labels = None
depends_on = None
SCHEMA = MigrationSettings().db_name


def upgrade() -> None:
    op.create_table(
        "admin_login_throttles",
        sa.Column("client_key_hash", sa.String(length=64), primary_key=True),
        sa.Column(
            "window_started_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.current_timestamp(),
            nullable=False,
        ),
        sa.Column("failure_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("blocked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.current_timestamp(),
            nullable=False,
        ),
        sa.CheckConstraint("failure_count >= 0", name="ck_admin_login_throttles_failure_count"),
        sa.CheckConstraint(
            "client_key_hash REGEXP '^[0-9a-f]{64}$'",
            name="ck_admin_login_throttles_key_hash",
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_admin_login_throttles_updated_at",
        "admin_login_throttles",
        ["updated_at"],
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_admin_login_throttles_updated_at",
        table_name="admin_login_throttles",
        schema=SCHEMA,
    )
    op.drop_table("admin_login_throttles", schema=SCHEMA)