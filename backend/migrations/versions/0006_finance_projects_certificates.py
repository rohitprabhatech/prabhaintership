"""Create enrollment finance, projects, certificates, and audit history on MySQL.

Revision ID: 0006_finance_projects_certificates
Revises: 0005_create_programs_batches_enrollments
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from app.config import MigrationSettings

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None
SCHEMA = MigrationSettings().db_name


def _table_exists(name: str) -> bool:
    if op.get_context().as_sql:
        return False
    return inspect(op.get_bind()).has_table(name, schema=SCHEMA)


def _create_table(name: str, *elements, **kwargs) -> None:
    if not _table_exists(name):
        op.create_table(name, *elements, **kwargs)


def _create_index(name: str, table_name: str, columns, **kwargs) -> None:
    if op.get_context().as_sql:
        op.create_index(name, table_name, columns, **kwargs)
        return
    existing = {index["name"] for index in inspect(op.get_bind()).get_indexes(table_name, schema=SCHEMA)}
    if name not in existing:
        op.create_index(name, table_name, columns, **kwargs)


def upgrade() -> None:
    _create_table(
        "fee_structures",
        sa.Column("fee_structure_id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("program_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("standard_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("currency", sa.CHAR(3), server_default=sa.text("'INR'"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_by", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.current_timestamp(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.current_timestamp(), nullable=False),
        sa.CheckConstraint("length(trim(name)) > 0", name="ck_fee_structures_name_not_blank"),
        sa.CheckConstraint("standard_amount > 0", name="ck_fee_structures_amount"),
        sa.CheckConstraint("currency = 'INR'", name="ck_fee_structures_currency"),
        sa.ForeignKeyConstraint(["program_id"], [f"{SCHEMA}.internship_programs.program_id"], name="fk_fee_structures_programs", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by"], [f"{SCHEMA}.admins.admin_id"], name="fk_fee_structures_created_by_admins", ondelete="RESTRICT"),
        sa.UniqueConstraint("program_id", "name", name="uq_fee_structures_program_name"),
        sa.UniqueConstraint("fee_structure_id", "program_id", name="uq_fee_structures_id_program"),
        schema=SCHEMA,
    )
    _create_index("ix_fee_structures_program_active", "fee_structures", ["program_id", "is_active"], schema=SCHEMA)

    _create_table(
        "enrollment_fee_terms",
        sa.Column("fee_term_id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("enrollment_id", sa.BigInteger(), nullable=False),
        sa.Column("current_enrollment_id", sa.BigInteger(), sa.Computed("CASE WHEN effective_to IS NULL THEN enrollment_id ELSE NULL END", persisted=True)),
        sa.Column("fee_structure_id", sa.BigInteger(), nullable=True),
        sa.Column("agreed_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("currency", sa.CHAR(3), server_default=sa.text("'INR'"), nullable=False),
        sa.Column("effective_from", sa.DateTime(), server_default=sa.func.current_timestamp(), nullable=False),
        sa.Column("effective_to", sa.DateTime(), nullable=True),
        sa.Column("reason", sa.String(500), nullable=False),
        sa.Column("created_by", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.current_timestamp(), nullable=False),
        sa.CheckConstraint("agreed_amount > 0", name="ck_fee_terms_amount"),
        sa.CheckConstraint("currency = 'INR'", name="ck_fee_terms_currency"),
        sa.CheckConstraint("effective_to IS NULL OR effective_to > effective_from", name="ck_fee_terms_effective_range"),
        sa.CheckConstraint("length(trim(reason)) > 0", name="ck_fee_terms_reason_not_blank"),
        sa.ForeignKeyConstraint(["enrollment_id"], [f"{SCHEMA}.enrollments.enrollment_id"], name="fk_fee_terms_enrollments", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["fee_structure_id"], [f"{SCHEMA}.fee_structures.fee_structure_id"], name="fk_fee_terms_fee_structures", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by"], [f"{SCHEMA}.admins.admin_id"], name="fk_fee_terms_created_by_admins", ondelete="RESTRICT"),
        schema=SCHEMA,
    )
    _create_index("ux_fee_terms_one_current_per_enrollment", "enrollment_fee_terms", ["current_enrollment_id"], unique=True, schema=SCHEMA)
    _create_index("ix_fee_terms_enrollment_history", "enrollment_fee_terms", ["enrollment_id", "effective_from"], schema=SCHEMA)

    _create_table(
        "fee_adjustments",
        sa.Column("fee_adjustment_id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("enrollment_id", sa.BigInteger(), nullable=False),
        sa.Column("adjustment_type", sa.String(20), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("idempotency_key", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("reason", sa.String(500), nullable=False),
        sa.Column("approved_by", sa.BigInteger(), nullable=False),
        sa.Column("approved_at", sa.DateTime(), server_default=sa.func.current_timestamp(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.current_timestamp(), nullable=False),
        sa.CheckConstraint("adjustment_type IN ('discount', 'fee_increase')", name="ck_fee_adjustments_type"),
        sa.CheckConstraint("amount > 0", name="ck_fee_adjustments_amount"),
        sa.CheckConstraint("length(trim(reason)) > 0", name="ck_fee_adjustments_reason"),
        sa.ForeignKeyConstraint(["enrollment_id"], [f"{SCHEMA}.enrollments.enrollment_id"], name="fk_fee_adjustments_enrollments", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["approved_by"], [f"{SCHEMA}.admins.admin_id"], name="fk_fee_adjustments_approved_by_admins", ondelete="RESTRICT"),
        sa.UniqueConstraint("idempotency_key", name="uq_fee_adjustments_idempotency_key"),
        schema=SCHEMA,
    )
    _create_index("ix_fee_adjustments_enrollment_time", "fee_adjustments", ["enrollment_id", "approved_at"], schema=SCHEMA)

    _create_table(
        "payments",
        sa.Column("payment_id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("enrollment_id", sa.BigInteger(), nullable=False),
        sa.Column("idempotency_key", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("currency", sa.CHAR(3), server_default=sa.text("'INR'"), nullable=False),
        sa.Column("paid_at", sa.DateTime(), nullable=False),
        sa.Column("payment_method", sa.String(32), nullable=False),
        sa.Column("payment_reference", sa.String(256), nullable=True),
        sa.Column("recorded_by", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.current_timestamp(), nullable=False),
        sa.CheckConstraint("amount > 0", name="ck_payments_amount"),
        sa.CheckConstraint("currency = 'INR'", name="ck_payments_currency"),
        sa.CheckConstraint("payment_method IN ('cash', 'bank_transfer', 'upi', 'card', 'cheque', 'other')", name="ck_payments_method"),
        sa.CheckConstraint("payment_reference IS NULL OR length(trim(payment_reference)) > 0", name="ck_payments_reference_not_blank"),
        sa.ForeignKeyConstraint(["enrollment_id"], [f"{SCHEMA}.enrollments.enrollment_id"], name="fk_payments_enrollments", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["recorded_by"], [f"{SCHEMA}.admins.admin_id"], name="fk_payments_recorded_by_admins", ondelete="RESTRICT"),
        sa.UniqueConstraint("payment_id", "enrollment_id", name="uq_payments_id_enrollment"),
        sa.UniqueConstraint("idempotency_key", name="uq_payments_idempotency_key"),
        schema=SCHEMA,
    )
    _create_index("ux_payments_method_reference", "payments", ["payment_method", "payment_reference"], unique=True, schema=SCHEMA)
    _create_index("ix_payments_enrollment_paid_at", "payments", ["enrollment_id", "paid_at", "payment_id"], schema=SCHEMA)

    _create_table(
        "payment_adjustments",
        sa.Column("adjustment_id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("payment_id", sa.BigInteger(), nullable=False),
        sa.Column("adjustment_type", sa.String(16), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("idempotency_key", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("reversal_payment_id", sa.BigInteger(), sa.Computed("CASE WHEN adjustment_type = 'reversal' THEN payment_id ELSE NULL END", persisted=True)),
        sa.Column("occurred_at", sa.DateTime(), server_default=sa.func.current_timestamp(), nullable=False),
        sa.Column("reason", sa.String(500), nullable=False),
        sa.Column("recorded_by", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.current_timestamp(), nullable=False),
        sa.CheckConstraint("adjustment_type IN ('refund', 'reversal')", name="ck_payment_adjustments_type"),
        sa.CheckConstraint("amount > 0", name="ck_payment_adjustments_amount"),
        sa.CheckConstraint("length(trim(reason)) > 0", name="ck_payment_adjustments_reason"),
        sa.ForeignKeyConstraint(["payment_id"], [f"{SCHEMA}.payments.payment_id"], name="fk_payment_adjustments_payments", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["recorded_by"], [f"{SCHEMA}.admins.admin_id"], name="fk_payment_adjustments_recorded_by_admins", ondelete="RESTRICT"),
        sa.UniqueConstraint("idempotency_key", name="uq_payment_adjustments_idempotency_key"),
        schema=SCHEMA,
    )
    _create_index("ix_payment_adjustments_payment_time", "payment_adjustments", ["payment_id", "occurred_at", "adjustment_id"], schema=SCHEMA)
    _create_index("ux_payment_adjustments_one_reversal", "payment_adjustments", ["reversal_payment_id"], unique=True, schema=SCHEMA)

    _create_table(
        "projects",
        sa.Column("project_id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("project_code", sa.String(64), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(16), server_default=sa.text("'active'"), nullable=False),
        sa.Column("created_by", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.current_timestamp(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.current_timestamp(), nullable=False),
        sa.CheckConstraint("length(trim(project_code)) > 0", name="ck_projects_code_not_blank"),
        sa.CheckConstraint("length(trim(name)) > 0", name="ck_projects_name_not_blank"),
        sa.CheckConstraint("status IN ('active', 'archived')", name="ck_projects_status"),
        sa.ForeignKeyConstraint(["created_by"], [f"{SCHEMA}.admins.admin_id"], name="fk_projects_created_by_admins", ondelete="RESTRICT"),
        sa.UniqueConstraint("project_code", name="uq_projects_project_code"),
        schema=SCHEMA,
    )

    _create_table(
        "project_assignments",
        sa.Column("project_assignment_id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("project_id", sa.BigInteger(), nullable=False),
        sa.Column("enrollment_id", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(16), server_default=sa.text("'assigned'"), nullable=False),
        sa.Column("assigned_at", sa.DateTime(), server_default=sa.func.current_timestamp(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("assigned_by", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.current_timestamp(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.current_timestamp(), nullable=False),
        sa.CheckConstraint("status IN ('assigned', 'in_progress', 'completed', 'cancelled')", name="ck_project_assignments_status"),
        sa.CheckConstraint("completed_at IS NULL OR completed_at >= assigned_at", name="ck_project_assignments_completion"),
        sa.ForeignKeyConstraint(["project_id"], [f"{SCHEMA}.projects.project_id"], name="fk_project_assignments_projects", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["enrollment_id"], [f"{SCHEMA}.enrollments.enrollment_id"], name="fk_project_assignments_enrollments", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["assigned_by"], [f"{SCHEMA}.admins.admin_id"], name="fk_project_assignments_assigned_by_admins", ondelete="RESTRICT"),
        sa.UniqueConstraint("project_id", "enrollment_id", name="uq_project_assignments_project_enrollment"),
        schema=SCHEMA,
    )
    _create_index("ix_project_assignments_enrollment_status", "project_assignments", ["enrollment_id", "status"], schema=SCHEMA)
    _create_index("ix_project_assignments_project_status", "project_assignments", ["project_id", "status"], schema=SCHEMA)

    _create_table(
        "certificates",
        sa.Column("certificate_id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("enrollment_id", sa.BigInteger(), nullable=False),
        sa.Column("certificate_number", sa.String(128), nullable=False),
        sa.Column("certificate_type", sa.String(128), nullable=False),
        sa.Column("issued_at", sa.DateTime(), nullable=False),
        sa.Column("document_uri", sa.String(2048), nullable=True),
        sa.Column("replaces_certificate_id", sa.BigInteger(), nullable=True),
        sa.Column("issued_by", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.current_timestamp(), nullable=False),
        sa.CheckConstraint("length(trim(certificate_number)) > 0", name="ck_certificates_number_not_blank"),
        sa.CheckConstraint("length(trim(certificate_type)) > 0", name="ck_certificates_type_not_blank"),
        sa.ForeignKeyConstraint(["enrollment_id"], [f"{SCHEMA}.enrollments.enrollment_id"], name="fk_certificates_enrollments", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["replaces_certificate_id"], [f"{SCHEMA}.certificates.certificate_id"], name="fk_certificates_replaces", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["issued_by"], [f"{SCHEMA}.admins.admin_id"], name="fk_certificates_issued_by_admins", ondelete="RESTRICT"),
        sa.UniqueConstraint("certificate_number", name="uq_certificates_certificate_number"),
        sa.UniqueConstraint("certificate_id", "enrollment_id", name="uq_certificates_id_enrollment"),
        schema=SCHEMA,
    )
    _create_index("ix_certificates_enrollment_issued", "certificates", ["enrollment_id", "issued_at"], schema=SCHEMA)
    _create_index("ix_certificates_replaces", "certificates", ["replaces_certificate_id"], schema=SCHEMA)

    _create_table(
        "certificate_events",
        sa.Column("certificate_event_id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("certificate_id", sa.BigInteger(), nullable=False),
        sa.Column("event_type", sa.String(16), nullable=False),
        sa.Column("terminal_certificate_id", sa.BigInteger(), sa.Computed("CASE WHEN event_type IN ('replaced', 'revoked') THEN certificate_id ELSE NULL END", persisted=True)),
        sa.Column("related_certificate_id", sa.BigInteger(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(), server_default=sa.func.current_timestamp(), nullable=False),
        sa.Column("reason", sa.String(500), nullable=False),
        sa.Column("recorded_by", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.current_timestamp(), nullable=False),
        sa.CheckConstraint("event_type IN ('replaced', 'revoked', 'corrected')", name="ck_certificate_events_type"),
        sa.CheckConstraint("length(trim(reason)) > 0", name="ck_certificate_events_reason"),
        sa.CheckConstraint("(event_type = 'replaced' AND related_certificate_id IS NOT NULL) OR (event_type IN ('revoked', 'corrected') AND related_certificate_id IS NULL)", name="ck_certificate_events_related"),
        sa.ForeignKeyConstraint(["certificate_id"], [f"{SCHEMA}.certificates.certificate_id"], name="fk_certificate_events_certificates", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["related_certificate_id"], [f"{SCHEMA}.certificates.certificate_id"], name="fk_certificate_events_related_certificates", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["recorded_by"], [f"{SCHEMA}.admins.admin_id"], name="fk_certificate_events_recorded_by_admins", ondelete="RESTRICT"),
        schema=SCHEMA,
    )
    _create_index("ix_certificate_events_certificate_time", "certificate_events", ["certificate_id", "occurred_at", "certificate_event_id"], schema=SCHEMA)
    _create_index("ux_certificate_events_one_terminal_state", "certificate_events", ["terminal_certificate_id"], unique=True, schema=SCHEMA)

    _create_table(
        "audit_logs",
        sa.Column("audit_log_id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("actor_admin_id", sa.BigInteger(), nullable=True),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("target_type", sa.String(64), nullable=True),
        sa.Column("target_id", sa.BigInteger(), nullable=True),
        sa.Column("outcome", sa.String(16), server_default=sa.text("'success'"), nullable=False),
        sa.Column("occurred_at", sa.DateTime(), server_default=sa.func.current_timestamp(), nullable=False),
        sa.Column("request_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("metadata", sa.JSON(), server_default=sa.text("(JSON_OBJECT())"), nullable=False),
        sa.CheckConstraint("length(trim(action)) > 0", name="ck_audit_action_not_blank"),
        sa.CheckConstraint("outcome IN ('success', 'failure', 'denied')", name="ck_audit_outcome"),
        sa.CheckConstraint("JSON_TYPE(metadata) = 'OBJECT'", name="ck_audit_metadata_object"),
        sa.ForeignKeyConstraint(["actor_admin_id"], [f"{SCHEMA}.admins.admin_id"], name="fk_audit_logs_actor_admins", ondelete="RESTRICT"),
        schema=SCHEMA,
    )
    _create_index("ix_audit_logs_time", "audit_logs", ["occurred_at", "audit_log_id"], schema=SCHEMA)
    _create_index("ix_audit_logs_target_time", "audit_logs", ["target_type", "target_id", "occurred_at"], schema=SCHEMA)
    _create_index("ix_audit_logs_actor_time", "audit_logs", ["actor_admin_id", "occurred_at"], schema=SCHEMA)


def downgrade() -> None:
    schema = SCHEMA
    for table in (
        "audit_logs",
        "certificate_events",
        "certificates",
        "project_assignments",
        "projects",
        "payment_adjustments",
        "payments",
        "fee_adjustments",
        "enrollment_fee_terms",
        "fee_structures",
    ):
        op.drop_table(table, schema=schema)
