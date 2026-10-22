"""Add MySQL financial and certificate guards plus derived views.

Revision ID: 0007_mysql_integrity_guards
Revises: 0006_finance_projects_certificates
"""

from alembic import op
from sqlalchemy import text
from app.config import MigrationSettings

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None
SCHEMA = MigrationSettings().db_name


def _trigger(name: str, timing: str, event: str, table: str, body: str) -> None:
    if not op.get_context().as_sql:
        existing = op.get_bind().execute(
            text("SELECT COUNT(*) FROM information_schema.triggers WHERE trigger_schema = :schema AND trigger_name = :name"),
            {"schema": SCHEMA, "name": name},
        ).scalar_one()
        if existing:
            return
    op.execute(
        f"""CREATE TRIGGER `{SCHEMA}`.`{name}` {timing} {event}
        ON `{SCHEMA}`.`{table}` FOR EACH ROW
        BEGIN
        {body}
        END"""
    )


def _immutable_triggers(table: str, label: str) -> None:
    _trigger(
        f"trg_{table}_no_update",
        "BEFORE",
        "UPDATE",
        table,
        f"SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = '{label} rows are append-only';",
    )
    _trigger(
        f"trg_{table}_no_delete",
        "BEFORE",
        "DELETE",
        table,
        f"SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = '{label} rows are append-only';",
    )


def upgrade() -> None:
    _create_views()
    _create_triggers()


def _create_views() -> None:
    op.execute(
        f"""CREATE OR REPLACE VIEW `{SCHEMA}`.`v_payment_status` AS
        SELECT p.payment_id, p.enrollment_id, p.idempotency_key, p.amount, p.currency,
               p.paid_at, p.payment_method, p.payment_reference, p.recorded_by, p.created_at,
               CAST(COALESCE(a.adjusted_amount, 0) AS DECIMAL(14,2)) AS adjusted_amount,
               CAST(p.amount - COALESCE(a.adjusted_amount, 0) AS DECIMAL(14,2)) AS net_amount,
               CASE
                   WHEN COALESCE(a.reversed_amount, 0) > 0 THEN 'reversed'
                   WHEN COALESCE(a.refunded_amount, 0) >= p.amount THEN 'refunded'
                   WHEN COALESCE(a.refunded_amount, 0) > 0 THEN 'partially_refunded'
                   ELSE 'posted'
               END AS derived_status
          FROM `{SCHEMA}`.payments AS p
          LEFT JOIN (
              SELECT payment_id,
                     SUM(amount) AS adjusted_amount,
                     SUM(CASE WHEN adjustment_type = 'refund' THEN amount ELSE 0 END) AS refunded_amount,
                     SUM(CASE WHEN adjustment_type = 'reversal' THEN amount ELSE 0 END) AS reversed_amount
                FROM `{SCHEMA}`.payment_adjustments
               GROUP BY payment_id
          ) AS a ON a.payment_id = p.payment_id"""
    )
    op.execute(
        f"""CREATE OR REPLACE VIEW `{SCHEMA}`.`v_enrollment_balances` AS
        SELECT e.enrollment_id, e.enrollment_number, e.student_id, e.program_id, e.batch_id,
               e.status AS enrollment_status, ft.fee_term_id, ft.agreed_amount AS fee_amount,
               ft.currency,
               CAST(COALESCE(fa.adjustments_total, 0) AS DECIMAL(14,2)) AS adjustments_total,
               CAST(GREATEST(ft.agreed_amount + COALESCE(fa.adjustments_total, 0), 0) AS DECIMAL(14,2)) AS effective_fee,
               CAST(COALESCE(pt.net_paid, 0) AS DECIMAL(14,2)) AS net_paid,
               CAST(GREATEST(ft.agreed_amount + COALESCE(fa.adjustments_total, 0) - COALESCE(pt.net_paid, 0), 0) AS DECIMAL(14,2)) AS pending_balance
          FROM `{SCHEMA}`.enrollments AS e
          JOIN `{SCHEMA}`.enrollment_fee_terms AS ft
            ON ft.enrollment_id = e.enrollment_id AND ft.effective_to IS NULL
          LEFT JOIN (
              SELECT enrollment_id,
                     SUM(CASE WHEN adjustment_type = 'fee_increase' THEN amount ELSE -amount END) AS adjustments_total
                FROM `{SCHEMA}`.fee_adjustments
               GROUP BY enrollment_id
          ) AS fa ON fa.enrollment_id = e.enrollment_id
          LEFT JOIN (
              SELECT enrollment_id, SUM(net_amount) AS net_paid
                FROM `{SCHEMA}`.v_payment_status
               GROUP BY enrollment_id
          ) AS pt ON pt.enrollment_id = e.enrollment_id"""
    )
    op.execute(
        f"""CREATE OR REPLACE VIEW `{SCHEMA}`.`v_certificate_status` AS
        SELECT c.certificate_id, c.enrollment_id, c.certificate_number, c.certificate_type,
               c.issued_at, c.document_uri, c.replaces_certificate_id, c.issued_by,
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


def _create_triggers() -> None:
    _trigger(
        "trg_fee_terms_insert_guard",
        "BEFORE",
        "INSERT",
        "enrollment_fee_terms",
        f"""
        DECLARE v_program_id BIGINT DEFAULT NULL;
        DECLARE v_adjustments DECIMAL(14,2) DEFAULT 0;
        DECLARE v_net_paid DECIMAL(14,2) DEFAULT 0;
        SELECT program_id INTO v_program_id FROM `{SCHEMA}`.enrollments WHERE enrollment_id = NEW.enrollment_id;
        IF v_program_id IS NULL THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Enrollment does not exist';
        END IF;
        IF NEW.fee_structure_id IS NOT NULL AND NOT EXISTS (
            SELECT 1 FROM `{SCHEMA}`.fee_structures
             WHERE fee_structure_id = NEW.fee_structure_id AND program_id = v_program_id
        ) THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Fee structure must belong to the enrollment program';
        END IF;
        IF EXISTS (
            SELECT 1 FROM `{SCHEMA}`.enrollment_fee_terms AS t
             WHERE t.enrollment_id = NEW.enrollment_id
               AND (NEW.effective_to IS NULL OR t.effective_from < NEW.effective_to)
               AND (t.effective_to IS NULL OR NEW.effective_from < t.effective_to)
        ) THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Enrollment fee-term ranges may not overlap';
        END IF;
        SELECT COALESCE(SUM(CASE WHEN adjustment_type = 'fee_increase' THEN amount ELSE -amount END), 0)
          INTO v_adjustments FROM `{SCHEMA}`.fee_adjustments WHERE enrollment_id = NEW.enrollment_id;
        SELECT COALESCE(SUM(net_amount), 0) INTO v_net_paid
          FROM `{SCHEMA}`.v_payment_status WHERE enrollment_id = NEW.enrollment_id;
        IF NEW.agreed_amount + v_adjustments < v_net_paid THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'New agreed fee cannot be less than net payments already received';
        END IF;""",
    )
    _trigger(
        "trg_fee_terms_update_guard",
        "BEFORE",
        "UPDATE",
        "enrollment_fee_terms",
        f"""
        IF OLD.effective_to IS NOT NULL OR NEW.effective_to IS NULL OR NEW.effective_to <= OLD.effective_from
           OR NOT (NEW.enrollment_id <=> OLD.enrollment_id)
           OR NOT (NEW.fee_structure_id <=> OLD.fee_structure_id)
           OR NOT (NEW.agreed_amount <=> OLD.agreed_amount)
           OR NOT (NEW.currency <=> OLD.currency)
           OR NOT (NEW.effective_from <=> OLD.effective_from)
           OR NOT (NEW.reason <=> OLD.reason)
           OR NOT (NEW.created_by <=> OLD.created_by)
           OR NOT (NEW.created_at <=> OLD.created_at) THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Fee terms are immutable; only the current term may be closed';
        END IF;""",
    )
    _trigger(
        "trg_fee_terms_no_delete",
        "BEFORE",
        "DELETE",
        "enrollment_fee_terms",
        "SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Fee term history is append-only';",
    )
    _trigger(
        "trg_fee_adjustments_insert_guard",
        "BEFORE",
        "INSERT",
        "fee_adjustments",
        f"""
        DECLARE v_fee DECIMAL(14,2) DEFAULT NULL;
        DECLARE v_adjustments DECIMAL(14,2) DEFAULT 0;
        DECLARE v_net_paid DECIMAL(14,2) DEFAULT 0;
        SELECT agreed_amount INTO v_fee FROM `{SCHEMA}`.enrollment_fee_terms
         WHERE enrollment_id = NEW.enrollment_id AND effective_to IS NULL;
        IF v_fee IS NULL THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Enrollment has no current fee term';
        END IF;
        SELECT v_fee + COALESCE(SUM(CASE WHEN adjustment_type = 'fee_increase' THEN amount ELSE -amount END), 0)
          INTO v_fee FROM `{SCHEMA}`.fee_adjustments WHERE enrollment_id = NEW.enrollment_id;
        SELECT COALESCE(SUM(net_amount), 0) INTO v_net_paid
          FROM `{SCHEMA}`.v_payment_status WHERE enrollment_id = NEW.enrollment_id;
        IF v_fee + IF(NEW.adjustment_type = 'fee_increase', NEW.amount, -NEW.amount) < 0
           OR v_fee + IF(NEW.adjustment_type = 'fee_increase', NEW.amount, -NEW.amount) < v_net_paid THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Fee adjustment cannot reduce the effective fee below net payments';
        END IF;""",
    )
    _immutable_triggers("fee_adjustments", "Fee adjustment")
    _trigger(
        "trg_payments_insert_guard",
        "BEFORE",
        "INSERT",
        "payments",
        f"""
        DECLARE v_fee DECIMAL(14,2) DEFAULT NULL;
        DECLARE v_adjustments DECIMAL(14,2) DEFAULT 0;
        DECLARE v_net_paid DECIMAL(14,2) DEFAULT 0;
        SELECT agreed_amount INTO v_fee FROM `{SCHEMA}`.enrollment_fee_terms
         WHERE enrollment_id = NEW.enrollment_id AND effective_to IS NULL;
        IF v_fee IS NULL THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Enrollment has no current fee term';
        END IF;
        SELECT COALESCE(SUM(CASE WHEN adjustment_type = 'fee_increase' THEN amount ELSE -amount END), 0)
          INTO v_adjustments FROM `{SCHEMA}`.fee_adjustments WHERE enrollment_id = NEW.enrollment_id;
        SELECT COALESCE(SUM(net_amount), 0) INTO v_net_paid
          FROM `{SCHEMA}`.v_payment_status WHERE enrollment_id = NEW.enrollment_id;
        IF NEW.amount > v_fee + v_adjustments - v_net_paid THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Payment exceeds enrollment balance';
        END IF;""",
    )
    _immutable_triggers("payments", "Payment")
    _trigger(
        "trg_payment_adjustments_insert_guard",
        "BEFORE",
        "INSERT",
        "payment_adjustments",
        f"""
        DECLARE v_enrollment_id BIGINT DEFAULT NULL;
        DECLARE v_payment_amount DECIMAL(14,2) DEFAULT NULL;
        DECLARE v_adjusted DECIMAL(14,2) DEFAULT 0;
        SELECT enrollment_id, amount INTO v_enrollment_id, v_payment_amount
          FROM `{SCHEMA}`.payments WHERE payment_id = NEW.payment_id;
        IF v_payment_amount IS NULL THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Payment does not exist';
        END IF;
        SELECT COALESCE(SUM(amount), 0) INTO v_adjusted
          FROM `{SCHEMA}`.payment_adjustments WHERE payment_id = NEW.payment_id;
        IF NEW.amount > v_payment_amount - v_adjusted THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Refund exceeds the remaining receipt amount';
        END IF;
        IF NEW.adjustment_type = 'reversal' AND NEW.amount <> v_payment_amount - v_adjusted THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Reversal must equal the remaining receipt amount';
        END IF;""",
    )
    _immutable_triggers("payment_adjustments", "Payment adjustment")
    _trigger(
        "trg_certificates_insert_guard",
        "BEFORE",
        "INSERT",
        "certificates",
        f"""
        DECLARE v_enrollment_id BIGINT DEFAULT NULL;
        DECLARE v_certificate_type VARCHAR(128) DEFAULT NULL;
        IF NEW.replaces_certificate_id IS NOT NULL THEN
                        SELECT enrollment_id, certificate_type INTO v_enrollment_id, v_certificate_type
                            FROM `{SCHEMA}`.certificates WHERE certificate_id = NEW.replaces_certificate_id;
                            IF NEW.replaces_certificate_id = NEW.certificate_id THEN
                                SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Certificate cannot replace itself';
                            END IF;
            IF v_enrollment_id IS NULL OR v_enrollment_id <> NEW.enrollment_id OR v_certificate_type <> NEW.certificate_type THEN
                SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Replacement must match the certificate enrollment and type';
            END IF;
            IF EXISTS (SELECT 1 FROM `{SCHEMA}`.certificate_events WHERE certificate_id = NEW.replaces_certificate_id AND event_type IN ('replaced', 'revoked')) THEN
                SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Certificate is already terminal';
            END IF;
        END IF;""",
    )
    _immutable_triggers("certificates", "Certificate issuance")
    _trigger(
        "trg_certificate_events_insert_guard",
        "BEFORE",
        "INSERT",
        "certificate_events",
        f"""
        DECLARE v_enrollment_id BIGINT DEFAULT NULL;
        DECLARE v_related_enrollment_id BIGINT DEFAULT NULL;
        DECLARE v_replacement_source BIGINT DEFAULT NULL;
        SELECT enrollment_id INTO v_enrollment_id FROM `{SCHEMA}`.certificates WHERE certificate_id = NEW.certificate_id;
        IF v_enrollment_id IS NULL THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Certificate does not exist';
        END IF;
        IF EXISTS (SELECT 1 FROM `{SCHEMA}`.certificate_events WHERE certificate_id = NEW.certificate_id AND event_type IN ('replaced', 'revoked')) THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Only an issued certificate can receive this event';
        END IF;
        IF NEW.related_certificate_id IS NOT NULL THEN
            IF NEW.related_certificate_id = NEW.certificate_id THEN
                SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Certificate event cannot reference itself';
            END IF;
            SELECT enrollment_id, replaces_certificate_id INTO v_related_enrollment_id, v_replacement_source
              FROM `{SCHEMA}`.certificates WHERE certificate_id = NEW.related_certificate_id;
            IF v_related_enrollment_id IS NULL OR v_related_enrollment_id <> v_enrollment_id THEN
                SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Related certificate must belong to the same enrollment';
            END IF;
            IF NEW.event_type = 'replaced' AND NOT (v_replacement_source <=> NEW.certificate_id) THEN
                SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Replacement link does not match event';
            END IF;
        END IF;""",
    )
    _immutable_triggers("certificate_events", "Certificate event")
    _immutable_triggers("audit_logs", "Audit log")


def downgrade() -> None:
    for table in ("audit_logs", "certificate_events", "certificates", "payment_adjustments", "payments", "fee_adjustments"):
        op.execute(f"DROP TRIGGER IF EXISTS `{SCHEMA}`.`trg_{table}_no_update`")
        op.execute(f"DROP TRIGGER IF EXISTS `{SCHEMA}`.`trg_{table}_no_delete`")
    for name in (
        "trg_fee_terms_insert_guard",
        "trg_fee_terms_update_guard",
        "trg_fee_terms_no_delete",
        "trg_fee_adjustments_insert_guard",
        "trg_payments_insert_guard",
        "trg_payment_adjustments_insert_guard",
        "trg_certificates_insert_guard",
        "trg_certificate_events_insert_guard",
    ):
        op.execute(f"DROP TRIGGER IF EXISTS `{SCHEMA}`.`{name}`")
    op.execute(f"DROP VIEW IF EXISTS `{SCHEMA}`.`v_enrollment_balances`")
    op.execute(f"DROP VIEW IF EXISTS `{SCHEMA}`.`v_certificate_status`")
    op.execute(f"DROP VIEW IF EXISTS `{SCHEMA}`.`v_payment_status`")
