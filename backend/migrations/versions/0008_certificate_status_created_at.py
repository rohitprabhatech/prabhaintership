"""Expose certificate creation timestamps in the status view.

Revision ID: 0008
Revises: 0007
"""

from alembic import op

from app.config import MigrationSettings

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None
SCHEMA = MigrationSettings().db_name


def _create_certificate_status_view(include_created_at: bool) -> None:
    created_at = ", c.created_at" if include_created_at else ""
    op.execute(
        f"""CREATE OR REPLACE VIEW `{SCHEMA}`.`v_certificate_status` AS
        SELECT c.certificate_id, c.enrollment_id, c.certificate_number, c.certificate_type,
               c.issued_at{created_at}, c.document_uri, c.replaces_certificate_id, c.issued_by,
               CASE WHEN terminal.event_type = 'revoked' THEN 'revoked'
                    WHEN terminal.event_type = 'replaced' THEN 'replaced'
                    ELSE 'issued' END AS derived_status,
               terminal.occurred_at AS terminal_event_at
          FROM `{SCHEMA}`.certificates AS c
          LEFT JOIN (
              SELECT certificate_id, MAX(event_type) AS event_type, MAX(occurred_at) AS occurred_at
                FROM `{SCHEMA}`.certificate_events
               WHERE event_type IN ('replaced', 'revoked')
               GROUP BY certificate_id
          ) AS terminal ON terminal.certificate_id = c.certificate_id"""
    )


def upgrade() -> None:
    _create_certificate_status_view(include_created_at=True)


def downgrade() -> None:
    _create_certificate_status_view(include_created_at=False)
