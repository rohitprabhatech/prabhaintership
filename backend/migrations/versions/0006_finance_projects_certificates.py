"""Add enrollment finance, projects, certificates, and audit history.

Revision ID: 0006_finance_projects_certificates
Revises: 0005_create_programs_batches_enrollments
Create Date: 2026-10-16
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0006_finance_projects_certificates"
down_revision = "0005_create_programs_batches_enrollments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    schema = "internship_management"

    op.create_table(
        "fee_structures",
        sa.Column("fee_structure_id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("program_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("standard_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("currency", sa.CHAR(3), server_default=sa.text("'INR'"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
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
        sa.CheckConstraint("length(btrim(name)) > 0", name="ck_fee_structures_name_not_blank"),
        sa.CheckConstraint("standard_amount > 0", name="ck_fee_structures_amount"),
        sa.CheckConstraint("currency = 'INR'", name="ck_fee_structures_currency"),
        sa.ForeignKeyConstraint(
            ["program_id"],
            [f"{schema}.internship_programs.program_id"],
            name="fk_fee_structures_programs",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            [f"{schema}.admins.admin_id"],
            name="fk_fee_structures_created_by_admins",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("program_id", "name", name="uq_fee_structures_program_name"),
        sa.UniqueConstraint("fee_structure_id", "program_id", name="uq_fee_structures_id_program"),
        schema=schema,
    )
    op.create_index(
        "ix_fee_structures_program_active",
        "fee_structures",
        ["program_id", "is_active"],
        schema=schema,
    )

    op.create_table(
        "enrollment_fee_terms",
        sa.Column("fee_term_id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("enrollment_id", sa.BigInteger(), nullable=False),
        sa.Column("fee_structure_id", sa.BigInteger(), nullable=True),
        sa.Column("agreed_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("currency", sa.CHAR(3), server_default=sa.text("'INR'"), nullable=False),
        sa.Column(
            "effective_from",
            sa.DateTime(timezone=True),
            server_default=sa.func.transaction_timestamp(),
            nullable=False,
        ),
        sa.Column("effective_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("created_by", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.transaction_timestamp(),
            nullable=False,
        ),
        sa.CheckConstraint("agreed_amount > 0", name="ck_fee_terms_amount"),
        sa.CheckConstraint("currency = 'INR'", name="ck_fee_terms_currency"),
        sa.CheckConstraint(
            "effective_to IS NULL OR effective_to > effective_from",
            name="ck_fee_terms_effective_range",
        ),
        sa.CheckConstraint("length(btrim(reason)) > 0", name="ck_fee_terms_reason_not_blank"),
        sa.ForeignKeyConstraint(
            ["enrollment_id"],
            [f"{schema}.enrollments.enrollment_id"],
            name="fk_fee_terms_enrollments",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["fee_structure_id"],
            [f"{schema}.fee_structures.fee_structure_id"],
            name="fk_fee_terms_fee_structures",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            [f"{schema}.admins.admin_id"],
            name="fk_fee_terms_created_by_admins",
            ondelete="RESTRICT",
        ),
        schema=schema,
    )
    op.create_index(
        "ux_fee_terms_one_current_per_enrollment",
        "enrollment_fee_terms",
        ["enrollment_id"],
        unique=True,
        schema=schema,
        postgresql_where=sa.text("effective_to IS NULL"),
    )
    op.create_index(
        "ix_fee_terms_enrollment_history",
        "enrollment_fee_terms",
        ["enrollment_id", sa.text("effective_from DESC")],
        schema=schema,
    )

    op.create_table(
        "fee_adjustments",
        sa.Column("fee_adjustment_id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("enrollment_id", sa.BigInteger(), nullable=False),
        sa.Column("adjustment_type", sa.Text(), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("idempotency_key", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("approved_by", sa.BigInteger(), nullable=False),
        sa.Column(
            "approved_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.transaction_timestamp(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.transaction_timestamp(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "adjustment_type IN ('discount', 'fee_increase')", name="ck_fee_adjustments_type"
        ),
        sa.CheckConstraint("amount > 0", name="ck_fee_adjustments_amount"),
        sa.CheckConstraint("length(btrim(reason)) > 0", name="ck_fee_adjustments_reason"),
        sa.ForeignKeyConstraint(
            ["enrollment_id"],
            [f"{schema}.enrollments.enrollment_id"],
            name="fk_fee_adjustments_enrollments",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["approved_by"],
            [f"{schema}.admins.admin_id"],
            name="fk_fee_adjustments_approved_by_admins",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("idempotency_key", name="uq_fee_adjustments_idempotency_key"),
        schema=schema,
    )
    op.create_index(
        "ix_fee_adjustments_enrollment_time",
        "fee_adjustments",
        ["enrollment_id", "approved_at"],
        schema=schema,
    )

    op.create_table(
        "payments",
        sa.Column("payment_id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("enrollment_id", sa.BigInteger(), nullable=False),
        sa.Column("idempotency_key", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("currency", sa.CHAR(3), server_default=sa.text("'INR'"), nullable=False),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payment_method", sa.Text(), nullable=False),
        sa.Column("payment_reference", sa.Text(), nullable=True),
        sa.Column("recorded_by", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.transaction_timestamp(),
            nullable=False,
        ),
        sa.CheckConstraint("amount > 0", name="ck_payments_amount"),
        sa.CheckConstraint("currency = 'INR'", name="ck_payments_currency"),
        sa.CheckConstraint(
            "payment_method IN ('cash', 'bank_transfer', 'upi', 'card', 'cheque', 'other')",
            name="ck_payments_method",
        ),
        sa.CheckConstraint(
            "payment_reference IS NULL OR length(btrim(payment_reference)) > 0",
            name="ck_payments_reference_not_blank",
        ),
        sa.ForeignKeyConstraint(
            ["enrollment_id"],
            [f"{schema}.enrollments.enrollment_id"],
            name="fk_payments_enrollments",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["recorded_by"],
            [f"{schema}.admins.admin_id"],
            name="fk_payments_recorded_by_admins",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("payment_id", "enrollment_id", name="uq_payments_id_enrollment"),
        schema=schema,
    )
    op.create_index(
        "ux_payments_idempotency_key", "payments", ["idempotency_key"], unique=True, schema=schema
    )
    op.create_index(
        "ux_payments_method_reference",
        "payments",
        ["payment_method", "payment_reference"],
        unique=True,
        schema=schema,
        postgresql_where=sa.text("payment_reference IS NOT NULL"),
    )
    op.create_index(
        "ix_payments_enrollment_paid_at",
        "payments",
        ["enrollment_id", sa.text("paid_at DESC"), "payment_id"],
        schema=schema,
    )

    op.create_table(
        "payment_adjustments",
        sa.Column("adjustment_id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("payment_id", sa.BigInteger(), nullable=False),
        sa.Column("adjustment_type", sa.Text(), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("idempotency_key", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.transaction_timestamp(),
            nullable=False,
        ),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("recorded_by", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.transaction_timestamp(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "adjustment_type IN ('refund', 'reversal')", name="ck_payment_adjustments_type"
        ),
        sa.CheckConstraint("amount > 0", name="ck_payment_adjustments_amount"),
        sa.CheckConstraint("length(btrim(reason)) > 0", name="ck_payment_adjustments_reason"),
        sa.ForeignKeyConstraint(
            ["payment_id"],
            [f"{schema}.payments.payment_id"],
            name="fk_payment_adjustments_payments",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["recorded_by"],
            [f"{schema}.admins.admin_id"],
            name="fk_payment_adjustments_recorded_by_admins",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("idempotency_key", name="uq_payment_adjustments_idempotency_key"),
        schema=schema,
    )
    op.create_index(
        "ix_payment_adjustments_payment_time",
        "payment_adjustments",
        ["payment_id", "occurred_at", "adjustment_id"],
        schema=schema,
    )
    op.create_index(
        "ux_payment_adjustments_one_reversal",
        "payment_adjustments",
        ["payment_id"],
        unique=True,
        schema=schema,
        postgresql_where=sa.text("adjustment_type = 'reversal'"),
    )

    op.create_table(
        "projects",
        sa.Column("project_id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("project_code", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
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
        sa.CheckConstraint("length(btrim(project_code)) > 0", name="ck_projects_code_not_blank"),
        sa.CheckConstraint("length(btrim(name)) > 0", name="ck_projects_name_not_blank"),
        sa.CheckConstraint("status IN ('active', 'archived')", name="ck_projects_status"),
        sa.ForeignKeyConstraint(
            ["created_by"],
            [f"{schema}.admins.admin_id"],
            name="fk_projects_created_by_admins",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("project_code", name="uq_projects_project_code"),
        schema=schema,
    )

    op.create_table(
        "project_assignments",
        sa.Column(
            "project_assignment_id", sa.BigInteger(), sa.Identity(always=True), primary_key=True
        ),
        sa.Column("project_id", sa.BigInteger(), nullable=False),
        sa.Column("enrollment_id", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.Text(), server_default=sa.text("'assigned'"), nullable=False),
        sa.Column(
            "assigned_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.transaction_timestamp(),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("assigned_by", sa.BigInteger(), nullable=False),
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
            "status IN ('assigned', 'in_progress', 'completed', 'cancelled')",
            name="ck_project_assignments_status",
        ),
        sa.CheckConstraint(
            "completed_at IS NULL OR completed_at >= assigned_at",
            name="ck_project_assignments_completion",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            [f"{schema}.projects.project_id"],
            name="fk_project_assignments_projects",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["enrollment_id"],
            [f"{schema}.enrollments.enrollment_id"],
            name="fk_project_assignments_enrollments",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["assigned_by"],
            [f"{schema}.admins.admin_id"],
            name="fk_project_assignments_assigned_by_admins",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "project_id", "enrollment_id", name="uq_project_assignments_project_enrollment"
        ),
        schema=schema,
    )
    op.create_index(
        "ix_project_assignments_enrollment_status",
        "project_assignments",
        ["enrollment_id", "status"],
        schema=schema,
    )
    op.create_index(
        "ix_project_assignments_project_status",
        "project_assignments",
        ["project_id", "status"],
        schema=schema,
    )

    op.create_table(
        "certificates",
        sa.Column("certificate_id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("enrollment_id", sa.BigInteger(), nullable=False),
        sa.Column("certificate_number", sa.Text(), nullable=False),
        sa.Column("certificate_type", sa.Text(), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("document_uri", sa.Text(), nullable=True),
        sa.Column("replaces_certificate_id", sa.BigInteger(), nullable=True),
        sa.Column("issued_by", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.transaction_timestamp(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "length(btrim(certificate_number)) > 0", name="ck_certificates_number_not_blank"
        ),
        sa.CheckConstraint(
            "length(btrim(certificate_type)) > 0", name="ck_certificates_type_not_blank"
        ),
        sa.CheckConstraint(
            "replaces_certificate_id IS NULL OR replaces_certificate_id <> certificate_id",
            name="ck_certificates_not_self_replacement",
        ),
        sa.ForeignKeyConstraint(
            ["enrollment_id"],
            [f"{schema}.enrollments.enrollment_id"],
            name="fk_certificates_enrollments",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["replaces_certificate_id"],
            [f"{schema}.certificates.certificate_id"],
            name="fk_certificates_replaces",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["issued_by"],
            [f"{schema}.admins.admin_id"],
            name="fk_certificates_issued_by_admins",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("certificate_number", name="uq_certificates_certificate_number"),
        sa.UniqueConstraint(
            "certificate_id", "enrollment_id", name="uq_certificates_id_enrollment"
        ),
        schema=schema,
    )
    op.create_index(
        "ix_certificates_enrollment_issued",
        "certificates",
        ["enrollment_id", sa.text("issued_at DESC")],
        schema=schema,
    )
    op.create_index(
        "ix_certificates_replaces",
        "certificates",
        ["replaces_certificate_id"],
        schema=schema,
        postgresql_where=sa.text("replaces_certificate_id IS NOT NULL"),
    )

    op.create_table(
        "certificate_events",
        sa.Column(
            "certificate_event_id", sa.BigInteger(), sa.Identity(always=True), primary_key=True
        ),
        sa.Column("certificate_id", sa.BigInteger(), nullable=False),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("related_certificate_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.transaction_timestamp(),
            nullable=False,
        ),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("recorded_by", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.transaction_timestamp(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "event_type IN ('replaced', 'revoked', 'corrected')",
            name="ck_certificate_events_type",
        ),
        sa.CheckConstraint(
            "related_certificate_id IS NULL OR related_certificate_id <> certificate_id",
            name="ck_certificate_events_not_self_related",
        ),
        sa.CheckConstraint("length(btrim(reason)) > 0", name="ck_certificate_events_reason"),
        sa.CheckConstraint(
            "(event_type = 'replaced' AND related_certificate_id IS NOT NULL) "
            "OR (event_type IN ('revoked', 'corrected') AND related_certificate_id IS NULL)",
            name="ck_certificate_events_related",
        ),
        sa.ForeignKeyConstraint(
            ["certificate_id"],
            [f"{schema}.certificates.certificate_id"],
            name="fk_certificate_events_certificates",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["related_certificate_id"],
            [f"{schema}.certificates.certificate_id"],
            name="fk_certificate_events_related_certificates",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["recorded_by"],
            [f"{schema}.admins.admin_id"],
            name="fk_certificate_events_recorded_by_admins",
            ondelete="RESTRICT",
        ),
        schema=schema,
    )
    op.create_index(
        "ix_certificate_events_certificate_time",
        "certificate_events",
        ["certificate_id", sa.text("occurred_at DESC"), sa.text("certificate_event_id DESC")],
        schema=schema,
    )
    op.create_index(
        "ux_certificate_events_one_terminal_state",
        "certificate_events",
        ["certificate_id"],
        unique=True,
        schema=schema,
        postgresql_where=sa.text("event_type IN ('replaced', 'revoked')"),
    )

    op.create_table(
        "audit_logs",
        sa.Column("audit_log_id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("actor_admin_id", sa.BigInteger(), nullable=True),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("target_type", sa.Text(), nullable=True),
        sa.Column("target_id", sa.BigInteger(), nullable=True),
        sa.Column("outcome", sa.Text(), server_default=sa.text("'success'"), nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.transaction_timestamp(),
            nullable=False,
        ),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.CheckConstraint("length(btrim(action)) > 0", name="ck_audit_action_not_blank"),
        sa.CheckConstraint("outcome IN ('success', 'failure', 'denied')", name="ck_audit_outcome"),
        sa.CheckConstraint("jsonb_typeof(metadata) = 'object'", name="ck_audit_metadata_object"),
        sa.ForeignKeyConstraint(
            ["actor_admin_id"],
            [f"{schema}.admins.admin_id"],
            name="fk_audit_logs_actor_admins",
            ondelete="RESTRICT",
        ),
        schema=schema,
    )
    op.create_index(
        "ix_audit_logs_time",
        "audit_logs",
        [sa.text("occurred_at DESC"), sa.text("audit_log_id DESC")],
        schema=schema,
    )
    op.create_index(
        "ix_audit_logs_target_time",
        "audit_logs",
        ["target_type", "target_id", sa.text("occurred_at DESC")],
        schema=schema,
        postgresql_where=sa.text("target_type IS NOT NULL AND target_id IS NOT NULL"),
    )
    op.create_index(
        "ix_audit_logs_actor_time",
        "audit_logs",
        ["actor_admin_id", sa.text("occurred_at DESC")],
        schema=schema,
        postgresql_where=sa.text("actor_admin_id IS NOT NULL"),
    )

    _create_functions_and_triggers(schema)
    _create_views(schema)


def _create_functions_and_triggers(schema: str) -> None:
    op.execute(
        f"""
        CREATE OR REPLACE FUNCTION {schema}.reject_immutable_row_change()
        RETURNS trigger LANGUAGE plpgsql
        SET search_path = {schema}, pg_temp
        AS $$
        BEGIN
            RAISE EXCEPTION '% rows are append-only and cannot be updated or deleted',
                TG_TABLE_NAME;
        END;
        $$;
        """
    )
    op.execute(
        f"""
        CREATE OR REPLACE FUNCTION {schema}.guard_enrollment_fee_term()
        RETURNS trigger LANGUAGE plpgsql
        SET search_path = {schema}, pg_temp
        AS $$
        DECLARE
            v_program_id bigint;
            v_effective_fee numeric(14,2);
            v_net_paid numeric(14,2);
        BEGIN
            IF TG_OP = 'UPDATE' THEN
                PERFORM 1 FROM enrollments WHERE enrollment_id = OLD.enrollment_id FOR UPDATE;
                IF OLD.effective_to IS NOT NULL OR NEW.effective_to IS NULL
                   OR NEW.effective_to <= OLD.effective_from
                     OR ROW(NEW.enrollment_id, NEW.fee_structure_id, NEW.agreed_amount,
                         NEW.currency, NEW.effective_from, NEW.reason,
                         NEW.created_by, NEW.created_at)
                      IS DISTINCT FROM
                      ROW(OLD.enrollment_id, OLD.fee_structure_id, OLD.agreed_amount,
                         OLD.currency, OLD.effective_from, OLD.reason,
                         OLD.created_by, OLD.created_at) THEN
                    RAISE EXCEPTION 'Fee terms are immutable; only the current term may be closed';
                END IF;
                RETURN NEW;
            END IF;

            SELECT program_id INTO v_program_id FROM enrollments
             WHERE enrollment_id = NEW.enrollment_id FOR UPDATE;
            IF NOT FOUND THEN RAISE EXCEPTION 'Enrollment does not exist'; END IF;
            IF NEW.fee_structure_id IS NOT NULL AND NOT EXISTS (
                SELECT 1 FROM fee_structures
                 WHERE fee_structure_id = NEW.fee_structure_id AND program_id = v_program_id
            ) THEN RAISE EXCEPTION 'Fee structure must belong to the enrollment program'; END IF;
            IF EXISTS (
                SELECT 1 FROM enrollment_fee_terms t
                 WHERE t.enrollment_id = NEW.enrollment_id
                   AND tstzrange(t.effective_from, t.effective_to, '[)')
                       && tstzrange(NEW.effective_from, NEW.effective_to, '[)')
            ) THEN RAISE EXCEPTION 'Enrollment fee-term ranges may not overlap'; END IF;

            SELECT NEW.agreed_amount + COALESCE(SUM(
                CASE WHEN adjustment_type = 'fee_increase' THEN amount ELSE -amount END
            ), 0) INTO v_effective_fee
              FROM fee_adjustments WHERE enrollment_id = NEW.enrollment_id;
            SELECT COALESCE(SUM(net_amount), 0) INTO v_net_paid
              FROM v_payment_status WHERE enrollment_id = NEW.enrollment_id;
            IF v_effective_fee < v_net_paid THEN
                RAISE EXCEPTION 'New agreed fee cannot be less than net payments already received';
            END IF;
            RETURN NEW;
        END;
        $$;
        CREATE TRIGGER trg_fee_terms_guard_insert BEFORE INSERT ON {schema}.enrollment_fee_terms
            FOR EACH ROW EXECUTE FUNCTION {schema}.guard_enrollment_fee_term();
        CREATE TRIGGER trg_fee_terms_guard_update BEFORE UPDATE ON {schema}.enrollment_fee_terms
            FOR EACH ROW EXECUTE FUNCTION {schema}.guard_enrollment_fee_term();
        CREATE TRIGGER trg_fee_terms_no_delete BEFORE DELETE ON {schema}.enrollment_fee_terms
            FOR EACH ROW EXECUTE FUNCTION {schema}.reject_immutable_row_change();
        """
    )
    op.execute(
        f"""
        CREATE OR REPLACE FUNCTION {schema}.require_current_fee_term()
        RETURNS trigger LANGUAGE plpgsql
        SET search_path = {schema}, pg_temp
        AS $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM enrollment_fee_terms
                 WHERE enrollment_id = NEW.enrollment_id AND effective_to IS NULL
            ) THEN RAISE EXCEPTION 'Enrollment must have a current fee term before commit'; END IF;
            RETURN NULL;
        END;
        $$;
        CREATE CONSTRAINT TRIGGER ct_enrollment_requires_fee_term
            AFTER INSERT ON {schema}.enrollments DEFERRABLE INITIALLY DEFERRED
            FOR EACH ROW EXECUTE FUNCTION {schema}.require_current_fee_term();
        CREATE CONSTRAINT TRIGGER ct_fee_terms_require_current
            AFTER INSERT OR UPDATE ON {schema}.enrollment_fee_terms DEFERRABLE INITIALLY DEFERRED
            FOR EACH ROW EXECUTE FUNCTION {schema}.require_current_fee_term();
        """
    )
    op.execute(
        f"""
        CREATE OR REPLACE FUNCTION {schema}.guard_fee_adjustment_insert()
        RETURNS trigger LANGUAGE plpgsql
        SET search_path = {schema}, pg_temp
        AS $$
        DECLARE
            v_fee numeric(14,2);
            v_net_paid numeric(14,2);
            v_effect numeric(14,2);
        BEGIN
            PERFORM 1 FROM enrollments WHERE enrollment_id = NEW.enrollment_id FOR UPDATE;
            SELECT agreed_amount INTO v_fee FROM enrollment_fee_terms
             WHERE enrollment_id = NEW.enrollment_id AND effective_to IS NULL;
            IF NOT FOUND THEN RAISE EXCEPTION 'Enrollment has no current fee term'; END IF;
            SELECT v_fee + COALESCE(SUM(
                CASE WHEN adjustment_type = 'fee_increase' THEN amount ELSE -amount END
            ), 0) INTO v_fee FROM fee_adjustments WHERE enrollment_id = NEW.enrollment_id;
            v_effect := CASE WHEN NEW.adjustment_type = 'fee_increase'
                             THEN NEW.amount ELSE -NEW.amount END;
            SELECT COALESCE(SUM(net_amount), 0) INTO v_net_paid
              FROM v_payment_status WHERE enrollment_id = NEW.enrollment_id;
            IF v_fee + v_effect < 0 OR v_fee + v_effect < v_net_paid THEN
                RAISE EXCEPTION 'Adjustment would reduce the fee below net payments';
            END IF;
            RETURN NEW;
        END;
        $$;
        CREATE TRIGGER trg_fee_adjustments_guard_insert
            BEFORE INSERT ON {schema}.fee_adjustments
            FOR EACH ROW EXECUTE FUNCTION {schema}.guard_fee_adjustment_insert();
        CREATE TRIGGER trg_fee_adjustments_immutable
            BEFORE UPDATE OR DELETE ON {schema}.fee_adjustments
            FOR EACH ROW EXECUTE FUNCTION {schema}.reject_immutable_row_change();
        """
    )
    op.execute(
        f"""
        CREATE OR REPLACE FUNCTION {schema}.guard_payment_insert()
        RETURNS trigger LANGUAGE plpgsql
        SET search_path = {schema}, pg_temp
        AS $$
        DECLARE
            v_fee numeric(14,2);
            v_net_paid numeric(14,2);
        BEGIN
            PERFORM 1 FROM enrollments WHERE enrollment_id = NEW.enrollment_id FOR UPDATE;
            IF NOT FOUND THEN RAISE EXCEPTION 'Enrollment does not exist'; END IF;
            SELECT agreed_amount INTO v_fee FROM enrollment_fee_terms
             WHERE enrollment_id = NEW.enrollment_id AND effective_to IS NULL;
            IF NOT FOUND THEN RAISE EXCEPTION 'Enrollment has no current fee term'; END IF;
            SELECT v_fee + COALESCE(SUM(
                CASE WHEN adjustment_type = 'fee_increase' THEN amount ELSE -amount END
            ), 0) INTO v_fee FROM fee_adjustments WHERE enrollment_id = NEW.enrollment_id;
            SELECT COALESCE(SUM(net_amount), 0) INTO v_net_paid
              FROM v_payment_status WHERE enrollment_id = NEW.enrollment_id;
            IF NEW.amount > v_fee - v_net_paid THEN
                RAISE EXCEPTION 'Payment exceeds enrollment balance';
            END IF;
            RETURN NEW;
        END;
        $$;
        CREATE TRIGGER trg_payments_guard_insert BEFORE INSERT ON {schema}.payments
            FOR EACH ROW EXECUTE FUNCTION {schema}.guard_payment_insert();
        CREATE TRIGGER trg_payments_immutable BEFORE UPDATE OR DELETE ON {schema}.payments
            FOR EACH ROW EXECUTE FUNCTION {schema}.reject_immutable_row_change();
        """
    )
    op.execute(
        f"""
        CREATE OR REPLACE FUNCTION {schema}.guard_payment_adjustment_insert()
        RETURNS trigger LANGUAGE plpgsql
        SET search_path = {schema}, pg_temp
        AS $$
        DECLARE
            v_enrollment_id bigint;
            v_payment_amount numeric(14,2);
            v_adjusted numeric(14,2);
        BEGIN
            SELECT enrollment_id INTO v_enrollment_id FROM payments
             WHERE payment_id = NEW.payment_id;
            IF NOT FOUND THEN RAISE EXCEPTION 'Payment does not exist'; END IF;
            PERFORM 1 FROM enrollments WHERE enrollment_id = v_enrollment_id FOR UPDATE;
            SELECT amount INTO v_payment_amount FROM payments
             WHERE payment_id = NEW.payment_id;
            SELECT COALESCE(SUM(amount), 0) INTO v_adjusted FROM payment_adjustments
             WHERE payment_id = NEW.payment_id;
            IF NEW.amount > v_payment_amount - v_adjusted THEN
                RAISE EXCEPTION 'Refund exceeds the remaining receipt amount';
            END IF;
            IF NEW.adjustment_type = 'reversal'
               AND NEW.amount <> v_payment_amount - v_adjusted THEN
                RAISE EXCEPTION 'Reversal must reverse the full remaining receipt amount';
            END IF;
            RETURN NEW;
        END;
        $$;
        CREATE TRIGGER trg_payment_adjustments_guard_insert
            BEFORE INSERT ON {schema}.payment_adjustments
            FOR EACH ROW EXECUTE FUNCTION {schema}.guard_payment_adjustment_insert();
        CREATE TRIGGER trg_payment_adjustments_immutable
            BEFORE UPDATE OR DELETE ON {schema}.payment_adjustments
            FOR EACH ROW EXECUTE FUNCTION {schema}.reject_immutable_row_change();
        """
    )
    op.execute(
        f"""
        CREATE OR REPLACE FUNCTION {schema}.guard_certificate_insert()
        RETURNS trigger LANGUAGE plpgsql
        SET search_path = {schema}, pg_temp
        AS $$
        DECLARE v_old_enrollment_id bigint; v_old_type text;
        BEGIN
            PERFORM 1 FROM enrollments WHERE enrollment_id = NEW.enrollment_id FOR UPDATE;
            IF NEW.replaces_certificate_id IS NOT NULL THEN
                SELECT enrollment_id, certificate_type INTO v_old_enrollment_id, v_old_type
                  FROM certificates WHERE certificate_id = NEW.replaces_certificate_id;
                IF NOT FOUND OR v_old_enrollment_id <> NEW.enrollment_id
                   OR v_old_type <> NEW.certificate_type THEN
                    RAISE EXCEPTION 'Replacement must match the certificate enrollment and type';
                END IF;
                IF EXISTS (
                    SELECT 1 FROM certificate_events
                     WHERE certificate_id = NEW.replaces_certificate_id
                       AND event_type IN ('replaced', 'revoked')
                ) THEN RAISE EXCEPTION 'Certificate is already terminal'; END IF;
            END IF;
            RETURN NEW;
        END;
        $$;
        CREATE TRIGGER trg_certificates_guard_insert BEFORE INSERT ON {schema}.certificates
            FOR EACH ROW EXECUTE FUNCTION {schema}.guard_certificate_insert();
        CREATE TRIGGER trg_certificates_immutable BEFORE UPDATE OR DELETE ON {schema}.certificates
            FOR EACH ROW EXECUTE FUNCTION {schema}.reject_immutable_row_change();
        """
    )
    op.execute(
        f"""
        CREATE OR REPLACE FUNCTION {schema}.guard_certificate_event_insert()
        RETURNS trigger LANGUAGE plpgsql
        SET search_path = {schema}, pg_temp
        AS $$
        DECLARE v_enrollment_id bigint; v_related_enrollment_id bigint; v_replacement_source bigint;
        BEGIN
            SELECT enrollment_id INTO v_enrollment_id FROM certificates
             WHERE certificate_id = NEW.certificate_id;
            IF NOT FOUND THEN RAISE EXCEPTION 'Certificate does not exist'; END IF;
            PERFORM 1 FROM enrollments WHERE enrollment_id = v_enrollment_id FOR UPDATE;
            IF NEW.related_certificate_id IS NOT NULL THEN
                SELECT enrollment_id, replaces_certificate_id
                  INTO v_related_enrollment_id, v_replacement_source
                  FROM certificates WHERE certificate_id = NEW.related_certificate_id;
                IF NOT FOUND OR v_related_enrollment_id <> v_enrollment_id THEN
                    RAISE EXCEPTION 'Related certificate must belong to the same enrollment';
                END IF;
                IF NEW.event_type = 'replaced'
                   AND v_replacement_source IS DISTINCT FROM NEW.certificate_id THEN
                    RAISE EXCEPTION 'Replacement link does not match event';
                END IF;
            END IF;
            RETURN NEW;
        END;
        $$;
        CREATE TRIGGER trg_certificate_events_guard_insert
            BEFORE INSERT ON {schema}.certificate_events
            FOR EACH ROW EXECUTE FUNCTION {schema}.guard_certificate_event_insert();
        CREATE TRIGGER trg_certificate_events_immutable
            BEFORE UPDATE OR DELETE ON {schema}.certificate_events
            FOR EACH ROW EXECUTE FUNCTION {schema}.reject_immutable_row_change();
        CREATE TRIGGER trg_audit_logs_immutable BEFORE UPDATE OR DELETE ON {schema}.audit_logs
            FOR EACH ROW EXECUTE FUNCTION {schema}.reject_immutable_row_change();
        """
    )
    op.execute(
        f"""
        CREATE OR REPLACE FUNCTION {schema}.require_replacement_event()
        RETURNS trigger LANGUAGE plpgsql
        SET search_path = {schema}, pg_temp
        AS $$
        BEGIN
            IF NEW.replaces_certificate_id IS NOT NULL AND NOT EXISTS (
                SELECT 1 FROM certificate_events
                 WHERE certificate_id = NEW.replaces_certificate_id
                   AND related_certificate_id = NEW.certificate_id
                   AND event_type = 'replaced'
            ) THEN RAISE EXCEPTION 'Replacement certificate requires a matching event'; END IF;
            RETURN NULL;
        END;
        $$;
        CREATE CONSTRAINT TRIGGER ct_certificate_replacement_event
            AFTER INSERT ON {schema}.certificates DEFERRABLE INITIALLY DEFERRED
            FOR EACH ROW EXECUTE FUNCTION {schema}.require_replacement_event();
        """
    )


def _create_views(schema: str) -> None:
    op.execute(
        f"""
        CREATE VIEW {schema}.v_payment_status AS
        SELECT p.payment_id, p.enrollment_id, p.idempotency_key, p.amount, p.currency,
               p.paid_at, p.payment_method, p.payment_reference, p.recorded_by, p.created_at,
               COALESCE(a.adjusted_amount, 0)::numeric(14,2) AS adjusted_amount,
               (p.amount - COALESCE(a.adjusted_amount, 0))::numeric(14,2) AS net_amount,
               CASE
                   WHEN COALESCE(a.reversed_amount, 0) > 0 THEN 'reversed'
                   WHEN COALESCE(a.refunded_amount, 0) >= p.amount THEN 'refunded'
                   WHEN COALESCE(a.refunded_amount, 0) > 0 THEN 'partially_refunded'
                   ELSE 'posted'
               END AS derived_status
          FROM {schema}.payments p
          LEFT JOIN (
              SELECT payment_id, SUM(amount) AS adjusted_amount,
                     SUM(amount) FILTER (WHERE adjustment_type = 'refund') AS refunded_amount,
                     SUM(amount) FILTER (WHERE adjustment_type = 'reversal') AS reversed_amount
                FROM {schema}.payment_adjustments GROUP BY payment_id
          ) a ON a.payment_id = p.payment_id;

        CREATE VIEW {schema}.v_enrollment_balances AS
        SELECT e.enrollment_id, e.enrollment_number, e.student_id, e.program_id, e.batch_id,
               e.status AS enrollment_status, ft.fee_term_id, ft.agreed_amount AS fee_amount,
               ft.currency,
               COALESCE(fa.adjustments_total, 0)::numeric(14,2) AS adjustments_total,
               GREATEST(ft.agreed_amount + COALESCE(fa.adjustments_total, 0), 0)::numeric(14,2)
                   AS effective_fee,
               COALESCE(pt.net_paid, 0)::numeric(14,2) AS net_paid,
               GREATEST(ft.agreed_amount + COALESCE(fa.adjustments_total, 0)
                        - COALESCE(pt.net_paid, 0), 0)::numeric(14,2) AS pending_balance
          FROM {schema}.enrollments e
          JOIN {schema}.enrollment_fee_terms ft
            ON ft.enrollment_id = e.enrollment_id AND ft.effective_to IS NULL
          LEFT JOIN (
              SELECT enrollment_id,
                     SUM(CASE WHEN adjustment_type = 'fee_increase' THEN amount ELSE -amount END)
                         AS adjustments_total
                FROM {schema}.fee_adjustments GROUP BY enrollment_id
          ) fa ON fa.enrollment_id = e.enrollment_id
          LEFT JOIN (
              SELECT enrollment_id, SUM(net_amount) AS net_paid
                FROM {schema}.v_payment_status GROUP BY enrollment_id
          ) pt ON pt.enrollment_id = e.enrollment_id;

        CREATE VIEW {schema}.v_certificate_status AS
        SELECT c.certificate_id, c.enrollment_id, c.certificate_number, c.certificate_type,
               c.issued_at, c.document_uri, c.replaces_certificate_id, c.issued_by,
               CASE WHEN terminal.event_type = 'revoked' THEN 'revoked'
                    WHEN terminal.event_type = 'replaced' THEN 'replaced'
                    ELSE 'issued' END AS derived_status,
               terminal.occurred_at AS terminal_event_at
          FROM {schema}.certificates c
          LEFT JOIN LATERAL (
              SELECT ce.event_type, ce.occurred_at
                FROM {schema}.certificate_events ce
               WHERE ce.certificate_id = c.certificate_id
                 AND ce.event_type IN ('replaced', 'revoked')
               ORDER BY ce.occurred_at DESC, ce.certificate_event_id DESC
               LIMIT 1
          ) terminal ON true;
        """
    )


def downgrade() -> None:
    schema = "internship_management"
    op.execute(f"DROP VIEW IF EXISTS {schema}.v_certificate_status")
    op.execute(f"DROP VIEW IF EXISTS {schema}.v_enrollment_balances")
    op.execute(f"DROP VIEW IF EXISTS {schema}.v_payment_status")
    op.execute(f"DROP FUNCTION IF EXISTS {schema}.require_replacement_event() CASCADE")
    op.execute(f"DROP FUNCTION IF EXISTS {schema}.guard_certificate_event_insert() CASCADE")
    op.execute(f"DROP FUNCTION IF EXISTS {schema}.guard_certificate_insert() CASCADE")
    op.execute(f"DROP FUNCTION IF EXISTS {schema}.guard_payment_adjustment_insert() CASCADE")
    op.execute(f"DROP FUNCTION IF EXISTS {schema}.guard_payment_insert() CASCADE")
    op.execute(f"DROP FUNCTION IF EXISTS {schema}.guard_fee_adjustment_insert() CASCADE")
    op.execute(f"DROP FUNCTION IF EXISTS {schema}.require_current_fee_term() CASCADE")
    op.execute(f"DROP FUNCTION IF EXISTS {schema}.guard_enrollment_fee_term() CASCADE")
    op.execute(f"DROP FUNCTION IF EXISTS {schema}.reject_immutable_row_change() CASCADE")
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
