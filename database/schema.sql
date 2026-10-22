-- MySQL 8.0.16+ reference baseline for a separate, empty local database.
-- Generated from current SQLAlchemy metadata and aligned with Alembic 0009.
-- Never run this baseline against an existing or production database.
-- Normal application setup should create an empty DB and run Alembic instead.

CREATE DATABASE internship_management_schema_template CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
USE internship_management_schema_template;
SET NAMES utf8mb4 COLLATE utf8mb4_0900_ai_ci;
SET default_storage_engine = InnoDB;


CREATE TABLE internship_management_schema_template.admin_login_throttles (
	client_key_hash VARCHAR(64) NOT NULL,
	window_started_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
	failure_count INTEGER NOT NULL DEFAULT 0,
	blocked_until DATETIME,
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (client_key_hash),
	CONSTRAINT ck_admin_login_throttles_failure_count CHECK (failure_count >= 0),
	CONSTRAINT ck_admin_login_throttles_key_hash CHECK (client_key_hash REGEXP '^[0-9a-f]{64}$')
);

CREATE INDEX ix_admin_login_throttles_updated_at ON internship_management_schema_template.admin_login_throttles (updated_at);

CREATE TABLE internship_management_schema_template.admins (
	admin_id BIGINT NOT NULL AUTO_INCREMENT,
	username VARCHAR(128) NOT NULL,
	email VARCHAR(254),
	email_normalized VARCHAR(254) GENERATED ALWAYS AS (lower(email)) STORED,
	password_hash VARCHAR(255) NOT NULL,
	is_active BOOL NOT NULL DEFAULT true,
	auth_version INTEGER NOT NULL DEFAULT 0,
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
	last_login_at DATETIME,
	PRIMARY KEY (admin_id),
	CONSTRAINT ck_admins_username_normalized CHECK (username = lower(username)),
	CONSTRAINT ck_admins_username_not_blank CHECK (length(trim(username)) > 0),
	CONSTRAINT ck_admins_password_hash_not_blank CHECK (length(trim(password_hash)) > 0),
	CONSTRAINT ck_admins_auth_version_nonnegative CHECK (auth_version >= 0),
	CONSTRAINT uq_admins_username UNIQUE (username)
);

CREATE UNIQUE INDEX ux_admins_email_lower ON internship_management_schema_template.admins (email_normalized);

CREATE TABLE internship_management_schema_template.business_number_counters (
	counter_id BIGINT NOT NULL AUTO_INCREMENT,
	entity_key VARCHAR(32) NOT NULL,
	calendar_year SMALLINT NOT NULL,
	counter_value BIGINT NOT NULL,
	PRIMARY KEY (counter_id),
	CONSTRAINT ck_business_number_counter_positive CHECK (counter_value > 0),
	CONSTRAINT uq_business_number_counter_period UNIQUE (entity_key, calendar_year)
);

CREATE TABLE internship_management_schema_template.audit_logs (
	audit_log_id BIGINT NOT NULL AUTO_INCREMENT,
	actor_admin_id BIGINT,
	action VARCHAR(64) NOT NULL,
	target_type VARCHAR(64),
	target_id BIGINT,
	outcome VARCHAR(16) NOT NULL DEFAULT 'success',
	occurred_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
	request_id CHAR(32),
	metadata JSON NOT NULL DEFAULT (JSON_OBJECT()),
	PRIMARY KEY (audit_log_id),
	CONSTRAINT ck_audit_action_not_blank CHECK (length(trim(action)) > 0),
	CONSTRAINT ck_audit_outcome CHECK (outcome IN ('success', 'failure', 'denied')),
	CONSTRAINT ck_audit_metadata_object CHECK (JSON_TYPE(metadata) = 'OBJECT'),
	CONSTRAINT fk_audit_logs_actor_admins FOREIGN KEY(actor_admin_id) REFERENCES internship_management_schema_template.admins (admin_id) ON DELETE RESTRICT
);

CREATE INDEX ix_audit_logs_actor_time ON internship_management_schema_template.audit_logs (actor_admin_id, occurred_at);

CREATE INDEX ix_audit_logs_target_time ON internship_management_schema_template.audit_logs (target_type, target_id, occurred_at);

CREATE INDEX ix_audit_logs_time ON internship_management_schema_template.audit_logs (occurred_at, audit_log_id);

CREATE TABLE internship_management_schema_template.internship_programs (
	program_id BIGINT NOT NULL AUTO_INCREMENT,
	program_code VARCHAR(64) NOT NULL,
	name VARCHAR(200) NOT NULL,
	name_search_key VARCHAR(200) GENERATED ALWAYS AS (lower(name)) STORED,
	description TEXT,
	status VARCHAR(16) NOT NULL DEFAULT 'draft',
	duration_months INTEGER,
	created_by BIGINT NOT NULL,
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (program_id),
	CONSTRAINT ck_program_code_not_blank CHECK (length(trim(program_code)) > 0),
	CONSTRAINT ck_program_name_not_blank CHECK (length(trim(name)) > 0),
	CONSTRAINT ck_program_duration_months_positive CHECK (duration_months IS NULL OR duration_months > 0),
	CONSTRAINT ck_program_status CHECK (status IN ('draft', 'active', 'inactive')),
	CONSTRAINT uq_internship_programs_program_code UNIQUE (program_code),
	CONSTRAINT fk_internship_programs_created_by_admins FOREIGN KEY(created_by) REFERENCES internship_management_schema_template.admins (admin_id) ON DELETE RESTRICT
);

CREATE INDEX ix_programs_status_name ON internship_management_schema_template.internship_programs (status, name_search_key);

CREATE TABLE internship_management_schema_template.projects (
	project_id BIGINT NOT NULL AUTO_INCREMENT,
	project_code VARCHAR(64) NOT NULL,
	name VARCHAR(200) NOT NULL,
	description TEXT,
	status VARCHAR(16) NOT NULL DEFAULT 'active',
	created_by BIGINT NOT NULL,
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (project_id),
	CONSTRAINT ck_projects_code_not_blank CHECK (length(trim(project_code)) > 0),
	CONSTRAINT ck_projects_name_not_blank CHECK (length(trim(name)) > 0),
	CONSTRAINT ck_projects_status CHECK (status IN ('active', 'archived')),
	CONSTRAINT uq_projects_project_code UNIQUE (project_code),
	CONSTRAINT fk_projects_created_by_admins FOREIGN KEY(created_by) REFERENCES internship_management_schema_template.admins (admin_id) ON DELETE RESTRICT
);

CREATE TABLE internship_management_schema_template.students (
	student_id BIGINT NOT NULL AUTO_INCREMENT,
	student_number VARCHAR(64) NOT NULL,
	full_name VARCHAR(200) NOT NULL,
	email VARCHAR(254),
	email_normalized VARCHAR(254) GENERATED ALWAYS AS (lower(email)) STORED,
	phone VARCHAR(64),
	address TEXT,
	city VARCHAR(120),
	state VARCHAR(120),
	postal_code VARCHAR(32),
	institution_name VARCHAR(200),
	course VARCHAR(200),
	internship_domain VARCHAR(120),
	name_search_key VARCHAR(200) GENERATED ALWAYS AS (lower(full_name)) STORED,
	status VARCHAR(16) NOT NULL DEFAULT 'active',
	created_by BIGINT NOT NULL,
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
	archived_at DATETIME,
	PRIMARY KEY (student_id),
	CONSTRAINT ck_students_name_not_blank CHECK (length(trim(full_name)) > 0),
	CONSTRAINT ck_students_status CHECK (status IN ('active', 'archived')),
	CONSTRAINT ck_students_archive_consistency CHECK ((status = 'archived' AND archived_at IS NOT NULL) OR (status = 'active' AND archived_at IS NULL)),
	CONSTRAINT uq_students_student_number UNIQUE (student_number),
	CONSTRAINT fk_students_created_by_admins FOREIGN KEY(created_by) REFERENCES internship_management_schema_template.admins (admin_id) ON DELETE RESTRICT
);

CREATE INDEX ix_students_status_created ON internship_management_schema_template.students (status, created_at);

CREATE INDEX ix_students_name_lower ON internship_management_schema_template.students (name_search_key);

CREATE UNIQUE INDEX ux_students_email_lower ON internship_management_schema_template.students (email_normalized);

CREATE TABLE internship_management_schema_template.batches (
	batch_id BIGINT NOT NULL AUTO_INCREMENT,
	program_id BIGINT NOT NULL,
	batch_code VARCHAR(64) NOT NULL,
	name VARCHAR(200) NOT NULL,
	starts_on DATE NOT NULL,
	ends_on DATE NOT NULL,
	capacity INTEGER,
	status VARCHAR(16) NOT NULL DEFAULT 'planned',
	created_by BIGINT NOT NULL,
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (batch_id),
	CONSTRAINT uq_batches_batch_code UNIQUE (batch_code),
	CONSTRAINT uq_batches_id_program UNIQUE (batch_id, program_id),
	CONSTRAINT ck_batches_code_not_blank CHECK (length(trim(batch_code)) > 0),
	CONSTRAINT ck_batches_name_not_blank CHECK (length(trim(name)) > 0),
	CONSTRAINT ck_batches_dates CHECK (ends_on >= starts_on),
	CONSTRAINT ck_batches_capacity CHECK (capacity IS NULL OR capacity > 0),
	CONSTRAINT ck_batches_status CHECK (status IN ('planned', 'active', 'completed', 'cancelled')),
	CONSTRAINT fk_batches_programs FOREIGN KEY(program_id) REFERENCES internship_management_schema_template.internship_programs (program_id) ON DELETE RESTRICT,
	CONSTRAINT fk_batches_created_by_admins FOREIGN KEY(created_by) REFERENCES internship_management_schema_template.admins (admin_id) ON DELETE RESTRICT
);

CREATE INDEX ix_batches_program_status_dates ON internship_management_schema_template.batches (program_id, status, starts_on, ends_on);

CREATE TABLE internship_management_schema_template.fee_structures (
	fee_structure_id BIGINT NOT NULL AUTO_INCREMENT,
	program_id BIGINT NOT NULL,
	name VARCHAR(200) NOT NULL,
	standard_amount NUMERIC(14, 2) NOT NULL,
	currency CHAR(3) NOT NULL DEFAULT 'INR',
	is_active BOOL NOT NULL DEFAULT true,
	created_by BIGINT NOT NULL,
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (fee_structure_id),
	CONSTRAINT uq_fee_structures_program_name UNIQUE (program_id, name),
	CONSTRAINT uq_fee_structures_id_program UNIQUE (fee_structure_id, program_id),
	CONSTRAINT ck_fee_structures_name_not_blank CHECK (length(trim(name)) > 0),
	CONSTRAINT ck_fee_structures_amount CHECK (standard_amount > 0),
	CONSTRAINT ck_fee_structures_currency CHECK (currency = 'INR'),
	CONSTRAINT fk_fee_structures_programs FOREIGN KEY(program_id) REFERENCES internship_management_schema_template.internship_programs (program_id) ON DELETE RESTRICT,
	CONSTRAINT fk_fee_structures_created_by_admins FOREIGN KEY(created_by) REFERENCES internship_management_schema_template.admins (admin_id) ON DELETE RESTRICT
);

CREATE INDEX ix_fee_structures_program_active ON internship_management_schema_template.fee_structures (program_id, is_active);

CREATE TABLE internship_management_schema_template.enrollments (
	enrollment_id BIGINT NOT NULL AUTO_INCREMENT,
	enrollment_number VARCHAR(64) NOT NULL,
	student_id BIGINT NOT NULL,
	program_id BIGINT NOT NULL,
	batch_id BIGINT NOT NULL,
	active_batch_key BIGINT GENERATED ALWAYS AS (CASE WHEN status = 'active' THEN COALESCE(batch_id, 0) ELSE NULL END) STORED,
	status VARCHAR(16) NOT NULL DEFAULT 'active',
	starts_on DATE NOT NULL,
	ends_on DATE,
	created_by BIGINT NOT NULL,
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (enrollment_id),
	CONSTRAINT fk_enrollments_batch_program FOREIGN KEY(batch_id, program_id) REFERENCES internship_management_schema_template.batches (batch_id, program_id) ON DELETE RESTRICT,
	CONSTRAINT uq_enrollments_enrollment_number UNIQUE (enrollment_number),
	CONSTRAINT uq_enrollments_id_program UNIQUE (enrollment_id, program_id),
	CONSTRAINT ck_enrollments_number_not_blank CHECK (length(trim(enrollment_number)) > 0),
	CONSTRAINT ck_enrollments_status CHECK (status IN ('active', 'completed', 'withdrawn', 'cancelled')),
	CONSTRAINT ck_enrollments_dates CHECK (ends_on IS NULL OR ends_on >= starts_on),
	CONSTRAINT fk_enrollments_students FOREIGN KEY(student_id) REFERENCES internship_management_schema_template.students (student_id) ON DELETE RESTRICT,
	CONSTRAINT fk_enrollments_programs FOREIGN KEY(program_id) REFERENCES internship_management_schema_template.internship_programs (program_id) ON DELETE RESTRICT,
	CONSTRAINT fk_enrollments_created_by_admins FOREIGN KEY(created_by) REFERENCES internship_management_schema_template.admins (admin_id) ON DELETE RESTRICT
);

CREATE INDEX ix_enrollments_student_created ON internship_management_schema_template.enrollments (student_id, created_at);

CREATE UNIQUE INDEX ux_enrollments_one_active_tuple ON internship_management_schema_template.enrollments (student_id, program_id, active_batch_key);

CREATE INDEX ix_enrollments_program_status ON internship_management_schema_template.enrollments (program_id, status, starts_on);

CREATE INDEX ix_enrollments_batch_status ON internship_management_schema_template.enrollments (batch_id, status);

CREATE TABLE internship_management_schema_template.certificates (
	certificate_id BIGINT NOT NULL AUTO_INCREMENT,
	enrollment_id BIGINT NOT NULL,
	certificate_number VARCHAR(128) NOT NULL,
	certificate_type VARCHAR(128) NOT NULL,
	issued_at DATETIME NOT NULL,
	document_uri VARCHAR(2048),
	replaces_certificate_id BIGINT,
	issued_by BIGINT NOT NULL,
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (certificate_id),
	CONSTRAINT ck_certificates_number_not_blank CHECK (length(trim(certificate_number)) > 0),
	CONSTRAINT ck_certificates_type_not_blank CHECK (length(trim(certificate_type)) > 0),
	CONSTRAINT uq_certificates_certificate_number UNIQUE (certificate_number),
	CONSTRAINT uq_certificates_id_enrollment UNIQUE (certificate_id, enrollment_id),
	CONSTRAINT fk_certificates_enrollments FOREIGN KEY(enrollment_id) REFERENCES internship_management_schema_template.enrollments (enrollment_id) ON DELETE RESTRICT,
	CONSTRAINT fk_certificates_replaces FOREIGN KEY(replaces_certificate_id) REFERENCES internship_management_schema_template.certificates (certificate_id) ON DELETE RESTRICT,
	CONSTRAINT fk_certificates_issued_by_admins FOREIGN KEY(issued_by) REFERENCES internship_management_schema_template.admins (admin_id) ON DELETE RESTRICT
);

CREATE INDEX ix_certificates_replaces ON internship_management_schema_template.certificates (replaces_certificate_id);

CREATE INDEX ix_certificates_enrollment_issued ON internship_management_schema_template.certificates (enrollment_id, issued_at);

CREATE TABLE internship_management_schema_template.enrollment_fee_terms (
	fee_term_id BIGINT NOT NULL AUTO_INCREMENT,
	enrollment_id BIGINT NOT NULL,
	current_enrollment_id BIGINT GENERATED ALWAYS AS (CASE WHEN effective_to IS NULL THEN enrollment_id ELSE NULL END) STORED,
	fee_structure_id BIGINT,
	agreed_amount NUMERIC(14, 2) NOT NULL,
	currency CHAR(3) NOT NULL DEFAULT 'INR',
	effective_from DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
	effective_to DATETIME,
	reason VARCHAR(500) NOT NULL,
	created_by BIGINT NOT NULL,
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (fee_term_id),
	CONSTRAINT ck_fee_terms_amount CHECK (agreed_amount > 0),
	CONSTRAINT ck_fee_terms_currency CHECK (currency = 'INR'),
	CONSTRAINT ck_fee_terms_effective_range CHECK (effective_to IS NULL OR effective_to > effective_from),
	CONSTRAINT ck_fee_terms_reason_not_blank CHECK (length(trim(reason)) > 0),
	CONSTRAINT fk_fee_terms_enrollments FOREIGN KEY(enrollment_id) REFERENCES internship_management_schema_template.enrollments (enrollment_id) ON DELETE RESTRICT,
	CONSTRAINT fk_fee_terms_fee_structures FOREIGN KEY(fee_structure_id) REFERENCES internship_management_schema_template.fee_structures (fee_structure_id) ON DELETE RESTRICT,
	CONSTRAINT fk_fee_terms_created_by_admins FOREIGN KEY(created_by) REFERENCES internship_management_schema_template.admins (admin_id) ON DELETE RESTRICT
);

CREATE UNIQUE INDEX ux_fee_terms_one_current_per_enrollment ON internship_management_schema_template.enrollment_fee_terms (current_enrollment_id);

CREATE INDEX ix_fee_terms_enrollment_history ON internship_management_schema_template.enrollment_fee_terms (enrollment_id, effective_from);

CREATE TABLE internship_management_schema_template.fee_adjustments (
	fee_adjustment_id BIGINT NOT NULL AUTO_INCREMENT,
	enrollment_id BIGINT NOT NULL,
	adjustment_type VARCHAR(20) NOT NULL,
	amount NUMERIC(14, 2) NOT NULL,
	idempotency_key CHAR(32) NOT NULL,
	reason VARCHAR(500) NOT NULL,
	approved_by BIGINT NOT NULL,
	approved_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (fee_adjustment_id),
	CONSTRAINT ck_fee_adjustments_type CHECK (adjustment_type IN ('discount', 'fee_increase')),
	CONSTRAINT ck_fee_adjustments_amount CHECK (amount > 0),
	CONSTRAINT ck_fee_adjustments_reason CHECK (length(trim(reason)) > 0),
	CONSTRAINT uq_fee_adjustments_idempotency_key UNIQUE (idempotency_key),
	CONSTRAINT fk_fee_adjustments_enrollments FOREIGN KEY(enrollment_id) REFERENCES internship_management_schema_template.enrollments (enrollment_id) ON DELETE RESTRICT,
	CONSTRAINT fk_fee_adjustments_approved_by_admins FOREIGN KEY(approved_by) REFERENCES internship_management_schema_template.admins (admin_id) ON DELETE RESTRICT
);

CREATE INDEX ix_fee_adjustments_enrollment_time ON internship_management_schema_template.fee_adjustments (enrollment_id, approved_at);

CREATE TABLE internship_management_schema_template.payments (
	payment_id BIGINT NOT NULL AUTO_INCREMENT,
	enrollment_id BIGINT NOT NULL,
	idempotency_key CHAR(32) NOT NULL,
	amount NUMERIC(14, 2) NOT NULL,
	currency CHAR(3) NOT NULL DEFAULT 'INR',
	paid_at DATETIME NOT NULL,
	payment_method VARCHAR(32) NOT NULL,
	payment_reference VARCHAR(256),
	recorded_by BIGINT NOT NULL,
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (payment_id),
	CONSTRAINT uq_payments_idempotency_key UNIQUE (idempotency_key),
	CONSTRAINT ck_payments_amount CHECK (amount > 0),
	CONSTRAINT ck_payments_currency CHECK (currency = 'INR'),
	CONSTRAINT ck_payments_method CHECK (payment_method IN ('cash', 'bank_transfer', 'upi', 'card', 'cheque', 'other')),
	CONSTRAINT uq_payments_id_enrollment UNIQUE (payment_id, enrollment_id),
	CONSTRAINT ck_payments_reference_not_blank CHECK (payment_reference IS NULL OR length(trim(payment_reference)) > 0),
	CONSTRAINT fk_payments_enrollments FOREIGN KEY(enrollment_id) REFERENCES internship_management_schema_template.enrollments (enrollment_id) ON DELETE RESTRICT,
	CONSTRAINT fk_payments_recorded_by_admins FOREIGN KEY(recorded_by) REFERENCES internship_management_schema_template.admins (admin_id) ON DELETE RESTRICT
);

CREATE UNIQUE INDEX ux_payments_method_reference ON internship_management_schema_template.payments (payment_method, payment_reference);

CREATE INDEX ix_payments_enrollment_paid_at ON internship_management_schema_template.payments (enrollment_id, paid_at, payment_id);

CREATE TABLE internship_management_schema_template.project_assignments (
	project_assignment_id BIGINT NOT NULL AUTO_INCREMENT,
	project_id BIGINT NOT NULL,
	enrollment_id BIGINT NOT NULL,
	status VARCHAR(16) NOT NULL DEFAULT 'assigned',
	assigned_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
	completed_at DATETIME,
	assigned_by BIGINT NOT NULL,
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (project_assignment_id),
	CONSTRAINT uq_project_assignments_project_enrollment UNIQUE (project_id, enrollment_id),
	CONSTRAINT ck_project_assignments_status CHECK (status IN ('assigned', 'in_progress', 'completed', 'cancelled')),
	CONSTRAINT ck_project_assignments_completion CHECK (completed_at IS NULL OR completed_at >= assigned_at),
	CONSTRAINT fk_project_assignments_projects FOREIGN KEY(project_id) REFERENCES internship_management_schema_template.projects (project_id) ON DELETE RESTRICT,
	CONSTRAINT fk_project_assignments_enrollments FOREIGN KEY(enrollment_id) REFERENCES internship_management_schema_template.enrollments (enrollment_id) ON DELETE RESTRICT,
	CONSTRAINT fk_project_assignments_assigned_by_admins FOREIGN KEY(assigned_by) REFERENCES internship_management_schema_template.admins (admin_id) ON DELETE RESTRICT
);

CREATE INDEX ix_project_assignments_project_status ON internship_management_schema_template.project_assignments (project_id, status);

CREATE INDEX ix_project_assignments_enrollment_status ON internship_management_schema_template.project_assignments (enrollment_id, status);

CREATE TABLE internship_management_schema_template.certificate_events (
	certificate_event_id BIGINT NOT NULL AUTO_INCREMENT,
	certificate_id BIGINT NOT NULL,
	event_type VARCHAR(16) NOT NULL,
	terminal_certificate_id BIGINT GENERATED ALWAYS AS (CASE WHEN event_type IN ('replaced', 'revoked') THEN certificate_id ELSE NULL END) STORED,
	related_certificate_id BIGINT,
	occurred_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
	reason VARCHAR(500) NOT NULL,
	recorded_by BIGINT NOT NULL,
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (certificate_event_id),
	CONSTRAINT ck_certificate_events_type CHECK (event_type IN ('replaced', 'revoked', 'corrected')),
	CONSTRAINT ck_certificate_events_reason CHECK (length(trim(reason)) > 0),
	CONSTRAINT ck_certificate_events_related CHECK ((event_type = 'replaced' AND related_certificate_id IS NOT NULL) OR (event_type IN ('revoked', 'corrected') AND related_certificate_id IS NULL)),
	CONSTRAINT fk_certificate_events_certificates FOREIGN KEY(certificate_id) REFERENCES internship_management_schema_template.certificates (certificate_id) ON DELETE RESTRICT,
	CONSTRAINT fk_certificate_events_related_certificates FOREIGN KEY(related_certificate_id) REFERENCES internship_management_schema_template.certificates (certificate_id) ON DELETE RESTRICT,
	CONSTRAINT fk_certificate_events_recorded_by_admins FOREIGN KEY(recorded_by) REFERENCES internship_management_schema_template.admins (admin_id) ON DELETE RESTRICT
);

CREATE UNIQUE INDEX ux_certificate_events_one_terminal_state ON internship_management_schema_template.certificate_events (terminal_certificate_id);

CREATE INDEX ix_certificate_events_certificate_time ON internship_management_schema_template.certificate_events (certificate_id, occurred_at, certificate_event_id);

CREATE TABLE internship_management_schema_template.payment_adjustments (
	adjustment_id BIGINT NOT NULL AUTO_INCREMENT,
	payment_id BIGINT NOT NULL,
	adjustment_type VARCHAR(16) NOT NULL,
	amount NUMERIC(14, 2) NOT NULL,
	idempotency_key CHAR(32) NOT NULL,
	reversal_payment_id BIGINT GENERATED ALWAYS AS (CASE WHEN adjustment_type = 'reversal' THEN payment_id ELSE NULL END) STORED,
	occurred_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
	reason VARCHAR(500) NOT NULL,
	recorded_by BIGINT NOT NULL,
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (adjustment_id),
	CONSTRAINT ck_payment_adjustments_type CHECK (adjustment_type IN ('refund', 'reversal')),
	CONSTRAINT ck_payment_adjustments_amount CHECK (amount > 0),
	CONSTRAINT ck_payment_adjustments_reason CHECK (length(trim(reason)) > 0),
	CONSTRAINT uq_payment_adjustments_idempotency_key UNIQUE (idempotency_key),
	CONSTRAINT fk_payment_adjustments_payments FOREIGN KEY(payment_id) REFERENCES internship_management_schema_template.payments (payment_id) ON DELETE RESTRICT,
	CONSTRAINT fk_payment_adjustments_recorded_by_admins FOREIGN KEY(recorded_by) REFERENCES internship_management_schema_template.admins (admin_id) ON DELETE RESTRICT
);

CREATE UNIQUE INDEX ux_payment_adjustments_one_reversal ON internship_management_schema_template.payment_adjustments (reversal_payment_id);

CREATE INDEX ix_payment_adjustments_payment_time ON internship_management_schema_template.payment_adjustments (payment_id, occurred_at, adjustment_id);

CREATE VIEW v_payment_status AS
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
  FROM payments AS p
  LEFT JOIN (
      SELECT payment_id,
             SUM(amount) AS adjusted_amount,
             SUM(CASE WHEN adjustment_type = 'refund' THEN amount ELSE 0 END) AS refunded_amount,
             SUM(CASE WHEN adjustment_type = 'reversal' THEN amount ELSE 0 END) AS reversed_amount
        FROM payment_adjustments
       GROUP BY payment_id
  ) AS a ON a.payment_id = p.payment_id;

CREATE VIEW v_enrollment_balances AS
SELECT e.enrollment_id, e.enrollment_number, e.student_id, e.program_id, e.batch_id,
       e.status AS enrollment_status, ft.fee_term_id, ft.agreed_amount AS fee_amount,
       ft.currency,
       CAST(COALESCE(fa.adjustments_total, 0) AS DECIMAL(14,2)) AS adjustments_total,
       CAST(GREATEST(ft.agreed_amount + COALESCE(fa.adjustments_total, 0), 0) AS DECIMAL(14,2)) AS effective_fee,
       CAST(COALESCE(pt.net_paid, 0) AS DECIMAL(14,2)) AS net_paid,
       CAST(GREATEST(ft.agreed_amount + COALESCE(fa.adjustments_total, 0) - COALESCE(pt.net_paid, 0), 0) AS DECIMAL(14,2)) AS pending_balance
  FROM enrollments AS e
  JOIN enrollment_fee_terms AS ft
    ON ft.enrollment_id = e.enrollment_id AND ft.effective_to IS NULL
  LEFT JOIN (
      SELECT enrollment_id,
             SUM(CASE WHEN adjustment_type = 'fee_increase' THEN amount ELSE -amount END) AS adjustments_total
        FROM fee_adjustments
       GROUP BY enrollment_id
  ) AS fa ON fa.enrollment_id = e.enrollment_id
  LEFT JOIN (
      SELECT enrollment_id, SUM(net_amount) AS net_paid
        FROM v_payment_status
       GROUP BY enrollment_id
  ) AS pt ON pt.enrollment_id = e.enrollment_id;

CREATE VIEW v_certificate_status AS
SELECT c.certificate_id, c.enrollment_id, c.certificate_number, c.certificate_type,
       c.issued_at, c.created_at, c.document_uri, c.replaces_certificate_id, c.issued_by,
       CASE WHEN terminal.event_type = 'revoked' THEN 'revoked'
            WHEN terminal.event_type = 'replaced' THEN 'replaced'
            ELSE 'issued' END AS derived_status,
       terminal.occurred_at AS terminal_event_at
  FROM certificates AS c
  LEFT JOIN (
      SELECT certificate_id, MAX(event_type) AS event_type, MAX(occurred_at) AS occurred_at
        FROM certificate_events
       WHERE event_type IN ('replaced', 'revoked')
       GROUP BY certificate_id
  ) AS terminal ON terminal.certificate_id = c.certificate_id;

DELIMITER $$

CREATE TRIGGER trg_fee_terms_insert_guard BEFORE INSERT ON enrollment_fee_terms
FOR EACH ROW
BEGIN
    DECLARE v_program_id BIGINT DEFAULT NULL;
    DECLARE v_adjustments DECIMAL(14,2) DEFAULT 0;
    DECLARE v_net_paid DECIMAL(14,2) DEFAULT 0;
    SELECT program_id INTO v_program_id FROM enrollments WHERE enrollment_id = NEW.enrollment_id;
    IF v_program_id IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Enrollment does not exist';
    END IF;
    IF NEW.fee_structure_id IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM fee_structures
         WHERE fee_structure_id = NEW.fee_structure_id AND program_id = v_program_id
    ) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Fee structure must belong to the enrollment program';
    END IF;
    IF EXISTS (
        SELECT 1 FROM enrollment_fee_terms AS t
         WHERE t.enrollment_id = NEW.enrollment_id
           AND (NEW.effective_to IS NULL OR t.effective_from < NEW.effective_to)
           AND (t.effective_to IS NULL OR NEW.effective_from < t.effective_to)
    ) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Enrollment fee-term ranges may not overlap';
    END IF;
    SELECT COALESCE(SUM(CASE WHEN adjustment_type = 'fee_increase' THEN amount ELSE -amount END), 0)
      INTO v_adjustments FROM fee_adjustments WHERE enrollment_id = NEW.enrollment_id;
    SELECT COALESCE(SUM(net_amount), 0) INTO v_net_paid
      FROM v_payment_status WHERE enrollment_id = NEW.enrollment_id;
    IF NEW.agreed_amount + v_adjustments < v_net_paid THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'New agreed fee cannot be less than net payments already received';
    END IF;
END$$

CREATE TRIGGER trg_fee_terms_update_guard BEFORE UPDATE ON enrollment_fee_terms
FOR EACH ROW
BEGIN
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
    END IF;
END$$

CREATE TRIGGER trg_fee_terms_no_delete BEFORE DELETE ON enrollment_fee_terms
FOR EACH ROW
BEGIN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Fee term history is append-only';
END$$

CREATE TRIGGER trg_fee_adjustments_insert_guard BEFORE INSERT ON fee_adjustments
FOR EACH ROW
BEGIN
    DECLARE v_fee DECIMAL(14,2) DEFAULT NULL;
    DECLARE v_net_paid DECIMAL(14,2) DEFAULT 0;
    SELECT agreed_amount INTO v_fee FROM enrollment_fee_terms
     WHERE enrollment_id = NEW.enrollment_id AND effective_to IS NULL;
    IF v_fee IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Enrollment has no current fee term';
    END IF;
    SELECT v_fee + COALESCE(SUM(CASE WHEN adjustment_type = 'fee_increase' THEN amount ELSE -amount END), 0)
      INTO v_fee FROM fee_adjustments WHERE enrollment_id = NEW.enrollment_id;
    SELECT COALESCE(SUM(net_amount), 0) INTO v_net_paid
      FROM v_payment_status WHERE enrollment_id = NEW.enrollment_id;
    IF v_fee + IF(NEW.adjustment_type = 'fee_increase', NEW.amount, -NEW.amount) < 0
       OR v_fee + IF(NEW.adjustment_type = 'fee_increase', NEW.amount, -NEW.amount) < v_net_paid THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Fee adjustment cannot reduce the effective fee below net payments';
    END IF;
END$$

CREATE TRIGGER trg_fee_adjustments_no_update BEFORE UPDATE ON fee_adjustments
FOR EACH ROW
BEGIN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Fee adjustment rows are append-only';
END$$

CREATE TRIGGER trg_fee_adjustments_no_delete BEFORE DELETE ON fee_adjustments
FOR EACH ROW
BEGIN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Fee adjustment rows are append-only';
END$$

CREATE TRIGGER trg_payments_insert_guard BEFORE INSERT ON payments
FOR EACH ROW
BEGIN
    DECLARE v_fee DECIMAL(14,2) DEFAULT NULL;
    DECLARE v_adjustments DECIMAL(14,2) DEFAULT 0;
    DECLARE v_net_paid DECIMAL(14,2) DEFAULT 0;
    SELECT agreed_amount INTO v_fee FROM enrollment_fee_terms
     WHERE enrollment_id = NEW.enrollment_id AND effective_to IS NULL;
    IF v_fee IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Enrollment has no current fee term';
    END IF;
    SELECT COALESCE(SUM(CASE WHEN adjustment_type = 'fee_increase' THEN amount ELSE -amount END), 0)
      INTO v_adjustments FROM fee_adjustments WHERE enrollment_id = NEW.enrollment_id;
    SELECT COALESCE(SUM(net_amount), 0) INTO v_net_paid
      FROM v_payment_status WHERE enrollment_id = NEW.enrollment_id;
    IF NEW.amount > v_fee + v_adjustments - v_net_paid THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Payment exceeds enrollment balance';
    END IF;
END$$

CREATE TRIGGER trg_payments_no_update BEFORE UPDATE ON payments
FOR EACH ROW
BEGIN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Payment rows are append-only';
END$$

CREATE TRIGGER trg_payments_no_delete BEFORE DELETE ON payments
FOR EACH ROW
BEGIN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Payment rows are append-only';
END$$

CREATE TRIGGER trg_payment_adjustments_insert_guard BEFORE INSERT ON payment_adjustments
FOR EACH ROW
BEGIN
    DECLARE v_payment_amount DECIMAL(14,2) DEFAULT NULL;
    DECLARE v_adjusted DECIMAL(14,2) DEFAULT 0;
    SELECT amount INTO v_payment_amount FROM payments WHERE payment_id = NEW.payment_id;
    IF v_payment_amount IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Payment does not exist';
    END IF;
    SELECT COALESCE(SUM(amount), 0) INTO v_adjusted
      FROM payment_adjustments WHERE payment_id = NEW.payment_id;
    IF NEW.amount > v_payment_amount - v_adjusted THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Refund exceeds the remaining receipt amount';
    END IF;
    IF NEW.adjustment_type = 'reversal' AND NEW.amount <> v_payment_amount - v_adjusted THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Reversal must equal the remaining receipt amount';
    END IF;
END$$

CREATE TRIGGER trg_payment_adjustments_no_update BEFORE UPDATE ON payment_adjustments
FOR EACH ROW
BEGIN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Payment adjustment rows are append-only';
END$$

CREATE TRIGGER trg_payment_adjustments_no_delete BEFORE DELETE ON payment_adjustments
FOR EACH ROW
BEGIN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Payment adjustment rows are append-only';
END$$

CREATE TRIGGER trg_certificates_insert_guard BEFORE INSERT ON certificates
FOR EACH ROW
BEGIN
    DECLARE v_enrollment_id BIGINT DEFAULT NULL;
    DECLARE v_certificate_type VARCHAR(128) DEFAULT NULL;
    IF NEW.replaces_certificate_id IS NOT NULL THEN
        SELECT enrollment_id, certificate_type INTO v_enrollment_id, v_certificate_type
          FROM certificates WHERE certificate_id = NEW.replaces_certificate_id;
        IF NEW.replaces_certificate_id = NEW.certificate_id THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Certificate cannot replace itself';
        END IF;
        IF v_enrollment_id IS NULL OR v_enrollment_id <> NEW.enrollment_id
           OR v_certificate_type <> NEW.certificate_type THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Replacement must match the certificate enrollment and type';
        END IF;
        IF EXISTS (
            SELECT 1 FROM certificate_events
             WHERE certificate_id = NEW.replaces_certificate_id AND event_type IN ('replaced', 'revoked')
        ) THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Certificate is already terminal';
        END IF;
    END IF;
END$$

CREATE TRIGGER trg_certificates_no_update BEFORE UPDATE ON certificates
FOR EACH ROW
BEGIN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Certificate issuance rows are append-only';
END$$

CREATE TRIGGER trg_certificates_no_delete BEFORE DELETE ON certificates
FOR EACH ROW
BEGIN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Certificate issuance rows are append-only';
END$$

CREATE TRIGGER trg_certificate_events_insert_guard BEFORE INSERT ON certificate_events
FOR EACH ROW
BEGIN
    DECLARE v_enrollment_id BIGINT DEFAULT NULL;
    DECLARE v_related_enrollment_id BIGINT DEFAULT NULL;
    DECLARE v_replacement_source BIGINT DEFAULT NULL;
    SELECT enrollment_id INTO v_enrollment_id
      FROM certificates WHERE certificate_id = NEW.certificate_id;
    IF v_enrollment_id IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Certificate does not exist';
    END IF;
    IF EXISTS (
        SELECT 1 FROM certificate_events
         WHERE certificate_id = NEW.certificate_id AND event_type IN ('replaced', 'revoked')
    ) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Only an issued certificate can receive this event';
    END IF;
    IF NEW.related_certificate_id IS NOT NULL THEN
        IF NEW.related_certificate_id = NEW.certificate_id THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Certificate event cannot reference itself';
        END IF;
        SELECT enrollment_id, replaces_certificate_id
          INTO v_related_enrollment_id, v_replacement_source
          FROM certificates WHERE certificate_id = NEW.related_certificate_id;
        IF v_related_enrollment_id IS NULL OR v_related_enrollment_id <> v_enrollment_id THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Related certificate must belong to the same enrollment';
        END IF;
        IF NEW.event_type = 'replaced' AND NOT (v_replacement_source <=> NEW.certificate_id) THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Replacement link does not match event';
        END IF;
    END IF;
END$$

CREATE TRIGGER trg_certificate_events_no_update BEFORE UPDATE ON certificate_events
FOR EACH ROW
BEGIN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Certificate event rows are append-only';
END$$

CREATE TRIGGER trg_certificate_events_no_delete BEFORE DELETE ON certificate_events
FOR EACH ROW
BEGIN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Certificate event rows are append-only';
END$$

CREATE TRIGGER trg_audit_logs_no_update BEFORE UPDATE ON audit_logs
FOR EACH ROW
BEGIN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Audit log rows are append-only';
END$$

CREATE TRIGGER trg_audit_logs_no_delete BEFORE DELETE ON audit_logs
FOR EACH ROW
BEGIN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Audit log rows are append-only';
END$$

DELIMITER ;
