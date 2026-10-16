-- Prabha Technology Pvt. Ltd. Internship Management System
-- PostgreSQL 14+ recommended. Execute once against a dedicated empty database.
-- This is a design baseline, not an Alembic migration. Production access grants,
-- roles, backup configuration, and secret provisioning are managed separately.

BEGIN;
CREATE SCHEMA IF NOT EXISTS internship_management;
SET LOCAL search_path TO internship_management, public;

CREATE TABLE admins (
    admin_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    username text NOT NULL UNIQUE,
    email text,
    password_hash text NOT NULL,
    is_active boolean NOT NULL DEFAULT true,
    auth_version integer NOT NULL DEFAULT 0,
    created_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
    updated_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
    last_login_at timestamptz,
    CONSTRAINT ck_admins_username_normalized CHECK (username = lower(username)),
    CONSTRAINT ck_admins_username_not_blank CHECK (length(btrim(username)) > 0),
    CONSTRAINT ck_admins_password_hash_not_blank CHECK (length(btrim(password_hash)) > 0),
    CONSTRAINT ck_admins_auth_version_nonnegative CHECK (auth_version >= 0)
);
CREATE UNIQUE INDEX ux_admins_email_lower
    ON admins (lower(email)) WHERE email IS NOT NULL;

CREATE TABLE admin_login_throttles (
    client_key_hash varchar(64) PRIMARY KEY,
    window_started_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
    failure_count integer NOT NULL DEFAULT 0,
    blocked_until timestamptz,
    updated_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
    CONSTRAINT ck_admin_login_throttles_failure_count CHECK (failure_count >= 0),
    CONSTRAINT ck_admin_login_throttles_key_hash CHECK (
        client_key_hash ~ '^[0-9a-f]{64}$'
    )
);
CREATE INDEX ix_admin_login_throttles_updated_at
    ON admin_login_throttles (updated_at);

CREATE TABLE students (
    student_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    student_number text NOT NULL UNIQUE,
    full_name text NOT NULL,
    email text,
    phone text,
    status text NOT NULL DEFAULT 'active',
    created_by bigint NOT NULL REFERENCES admins(admin_id) ON DELETE RESTRICT,
    created_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
    updated_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
    archived_at timestamptz,
    CONSTRAINT ck_students_name_not_blank CHECK (length(btrim(full_name)) > 0),
    CONSTRAINT ck_students_status CHECK (status IN ('active', 'archived')),
    CONSTRAINT ck_students_archive_consistency CHECK (
        (status = 'archived' AND archived_at IS NOT NULL)
        OR (status = 'active' AND archived_at IS NULL)
    )
);
CREATE UNIQUE INDEX ux_students_email_lower
    ON students (lower(email)) WHERE email IS NOT NULL;
CREATE INDEX ix_students_name_lower ON students (lower(full_name));
CREATE INDEX ix_students_status_created ON students (status, created_at DESC);

CREATE TABLE internship_programs (
    program_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    program_code text NOT NULL UNIQUE,
    name text NOT NULL,
    description text,
    status text NOT NULL DEFAULT 'draft',
    created_by bigint NOT NULL REFERENCES admins(admin_id) ON DELETE RESTRICT,
    created_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
    updated_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
    CONSTRAINT ck_program_code_not_blank CHECK (length(btrim(program_code)) > 0),
    CONSTRAINT ck_program_name_not_blank CHECK (length(btrim(name)) > 0),
    CONSTRAINT ck_program_status CHECK (status IN ('draft', 'active', 'inactive'))
);
CREATE INDEX ix_programs_status_name ON internship_programs (status, lower(name));

CREATE TABLE batches (
    batch_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    program_id bigint NOT NULL REFERENCES internship_programs(program_id) ON DELETE RESTRICT,
    batch_code text NOT NULL,
    name text NOT NULL,
    starts_on date NOT NULL,
    ends_on date NOT NULL,
    capacity integer,
    status text NOT NULL DEFAULT 'planned',
    created_by bigint NOT NULL REFERENCES admins(admin_id) ON DELETE RESTRICT,
    created_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
    updated_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
    CONSTRAINT uq_batches_program_code UNIQUE (program_id, batch_code),
    CONSTRAINT uq_batches_id_program UNIQUE (batch_id, program_id),
    CONSTRAINT ck_batches_code_not_blank CHECK (length(btrim(batch_code)) > 0),
    CONSTRAINT ck_batches_name_not_blank CHECK (length(btrim(name)) > 0),
    CONSTRAINT ck_batches_dates CHECK (ends_on >= starts_on),
    CONSTRAINT ck_batches_capacity CHECK (capacity IS NULL OR capacity > 0),
    CONSTRAINT ck_batches_status CHECK (status IN ('planned', 'active', 'completed', 'cancelled'))
);
CREATE INDEX ix_batches_program_status_dates
    ON batches (program_id, status, starts_on, ends_on);

CREATE TABLE enrollments (
    enrollment_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    enrollment_number text NOT NULL UNIQUE,
    student_id bigint NOT NULL REFERENCES students(student_id) ON DELETE RESTRICT,
    program_id bigint NOT NULL REFERENCES internship_programs(program_id) ON DELETE RESTRICT,
    batch_id bigint,
    status text NOT NULL DEFAULT 'active',
    starts_on date NOT NULL,
    ends_on date,
    created_by bigint NOT NULL REFERENCES admins(admin_id) ON DELETE RESTRICT,
    created_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
    updated_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
    CONSTRAINT fk_enrollments_batch_program
        FOREIGN KEY (batch_id, program_id)
        REFERENCES batches(batch_id, program_id) ON DELETE RESTRICT,
    CONSTRAINT uq_enrollments_id_program UNIQUE (enrollment_id, program_id),
    CONSTRAINT ck_enrollments_number_not_blank CHECK (length(btrim(enrollment_number)) > 0),
    CONSTRAINT ck_enrollments_status CHECK (
        status IN ('active', 'completed', 'withdrawn', 'cancelled')
    ),
    CONSTRAINT ck_enrollments_dates CHECK (ends_on IS NULL OR ends_on >= starts_on)
);
CREATE INDEX ix_enrollments_student_created
    ON enrollments (student_id, created_at DESC);
CREATE INDEX ix_enrollments_program_status
    ON enrollments (program_id, status, starts_on);
CREATE INDEX ix_enrollments_batch_status
    ON enrollments (batch_id, status) WHERE batch_id IS NOT NULL;
-- Assumption: duplicate active enrollment in the same student/program/batch tuple
-- is forbidden; completed/withdrawn/cancelled history remains repeatable.
-- A null batch is normalized to sentinel 0 for this index only; identity IDs are positive.
CREATE UNIQUE INDEX ux_enrollments_one_active_tuple
    ON enrollments (student_id, program_id, (COALESCE(batch_id, 0)))
    WHERE status = 'active';

CREATE TABLE fee_structures (
    fee_structure_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    program_id bigint NOT NULL REFERENCES internship_programs(program_id) ON DELETE RESTRICT,
    name text NOT NULL,
    standard_amount numeric(14, 2) NOT NULL,
    currency char(3) NOT NULL DEFAULT 'INR',
    is_active boolean NOT NULL DEFAULT true,
    created_by bigint NOT NULL REFERENCES admins(admin_id) ON DELETE RESTRICT,
    created_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
    updated_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
    CONSTRAINT uq_fee_structures_program_name UNIQUE (program_id, name),
    CONSTRAINT uq_fee_structures_id_program UNIQUE (fee_structure_id, program_id),
    CONSTRAINT ck_fee_structures_name_not_blank CHECK (length(btrim(name)) > 0),
    CONSTRAINT ck_fee_structures_amount CHECK (standard_amount > 0),
    CONSTRAINT ck_fee_structures_currency CHECK (currency = 'INR')
);
CREATE INDEX ix_fee_structures_program_active
    ON fee_structures (program_id, is_active);

CREATE TABLE enrollment_fee_terms (
    fee_term_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    enrollment_id bigint NOT NULL REFERENCES enrollments(enrollment_id) ON DELETE RESTRICT,
    fee_structure_id bigint REFERENCES fee_structures(fee_structure_id) ON DELETE RESTRICT,
    agreed_amount numeric(14, 2) NOT NULL,
    currency char(3) NOT NULL DEFAULT 'INR',
    effective_from timestamptz NOT NULL DEFAULT transaction_timestamp(),
    effective_to timestamptz,
    reason text NOT NULL,
    created_by bigint NOT NULL REFERENCES admins(admin_id) ON DELETE RESTRICT,
    created_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
    CONSTRAINT ck_fee_terms_amount CHECK (agreed_amount > 0),
    CONSTRAINT ck_fee_terms_currency CHECK (currency = 'INR'),
    CONSTRAINT ck_fee_terms_effective_range CHECK (
        effective_to IS NULL OR effective_to > effective_from
    ),
    CONSTRAINT ck_fee_terms_reason_not_blank CHECK (length(btrim(reason)) > 0)
);
CREATE UNIQUE INDEX ux_fee_terms_one_current_per_enrollment
    ON enrollment_fee_terms (enrollment_id) WHERE effective_to IS NULL;
CREATE INDEX ix_fee_terms_enrollment_history
    ON enrollment_fee_terms (enrollment_id, effective_from DESC);

CREATE TABLE fee_adjustments (
    fee_adjustment_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    enrollment_id bigint NOT NULL REFERENCES enrollments(enrollment_id) ON DELETE RESTRICT,
    adjustment_type text NOT NULL,
    amount numeric(14, 2) NOT NULL,
    idempotency_key uuid NOT NULL UNIQUE,
    reason text NOT NULL,
    approved_by bigint NOT NULL REFERENCES admins(admin_id) ON DELETE RESTRICT,
    approved_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
    created_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
    CONSTRAINT ck_fee_adjustments_type CHECK (
        adjustment_type IN ('discount', 'fee_increase')
    ),
    CONSTRAINT ck_fee_adjustments_amount CHECK (amount > 0),
    CONSTRAINT ck_fee_adjustments_reason CHECK (length(btrim(reason)) > 0)
);
CREATE INDEX ix_fee_adjustments_enrollment_time
    ON fee_adjustments (enrollment_id, approved_at);

CREATE TABLE payments (
    payment_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    enrollment_id bigint NOT NULL REFERENCES enrollments(enrollment_id) ON DELETE RESTRICT,
    idempotency_key uuid NOT NULL UNIQUE,
    amount numeric(14, 2) NOT NULL,
    currency char(3) NOT NULL DEFAULT 'INR',
    paid_at timestamptz NOT NULL,
    payment_method text NOT NULL,
    payment_reference text,
    recorded_by bigint NOT NULL REFERENCES admins(admin_id) ON DELETE RESTRICT,
    created_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
    CONSTRAINT uq_payments_id_enrollment UNIQUE (payment_id, enrollment_id),
    CONSTRAINT ck_payments_amount CHECK (amount > 0),
    CONSTRAINT ck_payments_currency CHECK (currency = 'INR'),
    CONSTRAINT ck_payments_method CHECK (
        payment_method IN ('cash', 'bank_transfer', 'upi', 'card', 'cheque', 'other')
    ),
    CONSTRAINT ck_payments_reference_not_blank CHECK (
        payment_reference IS NULL OR length(btrim(payment_reference)) > 0
    )
);

CREATE INDEX ix_payments_enrollment_paid_at
    ON payments (enrollment_id, paid_at DESC, payment_id DESC);
CREATE UNIQUE INDEX ux_payments_method_reference
    ON payments (payment_method, payment_reference)
    WHERE payment_reference IS NOT NULL;

CREATE TABLE payment_adjustments (
    adjustment_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    payment_id bigint NOT NULL REFERENCES payments(payment_id) ON DELETE RESTRICT,
    adjustment_type text NOT NULL,
    amount numeric(14, 2) NOT NULL,
    idempotency_key uuid NOT NULL UNIQUE,
    occurred_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
    reason text NOT NULL,
    recorded_by bigint NOT NULL REFERENCES admins(admin_id) ON DELETE RESTRICT,
    created_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
    CONSTRAINT ck_payment_adjustments_type CHECK (
        adjustment_type IN ('refund', 'reversal')
    ),
    CONSTRAINT ck_payment_adjustments_amount CHECK (amount > 0),
    CONSTRAINT ck_payment_adjustments_reason CHECK (length(btrim(reason)) > 0)
);

CREATE INDEX ix_payment_adjustments_payment_time
    ON payment_adjustments (payment_id, occurred_at, adjustment_id);
CREATE UNIQUE INDEX ux_payment_adjustments_one_reversal
    ON payment_adjustments (payment_id) WHERE adjustment_type = 'reversal';

CREATE TABLE projects (
    project_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    project_code text NOT NULL UNIQUE,
    name text NOT NULL,
    description text,
    status text NOT NULL DEFAULT 'active',
    created_by bigint NOT NULL REFERENCES admins(admin_id) ON DELETE RESTRICT,
    created_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
    updated_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
    CONSTRAINT ck_projects_code_not_blank CHECK (length(btrim(project_code)) > 0),
    CONSTRAINT ck_projects_name_not_blank CHECK (length(btrim(name)) > 0),
    CONSTRAINT ck_projects_status CHECK (status IN ('active', 'archived'))
);

CREATE TABLE project_assignments (
    project_assignment_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    project_id bigint NOT NULL REFERENCES projects(project_id) ON DELETE RESTRICT,
    enrollment_id bigint NOT NULL REFERENCES enrollments(enrollment_id) ON DELETE RESTRICT,
    status text NOT NULL DEFAULT 'assigned',
    assigned_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
    completed_at timestamptz,
    assigned_by bigint NOT NULL REFERENCES admins(admin_id) ON DELETE RESTRICT,
    created_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
    updated_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
    CONSTRAINT uq_project_assignments_project_enrollment UNIQUE (project_id, enrollment_id),
    CONSTRAINT ck_project_assignments_status CHECK (
        status IN ('assigned', 'in_progress', 'completed', 'cancelled')
    ),
    CONSTRAINT ck_project_assignments_completion CHECK (
        completed_at IS NULL OR completed_at >= assigned_at
    )
);
CREATE INDEX ix_project_assignments_enrollment_status
    ON project_assignments (enrollment_id, status);
CREATE INDEX ix_project_assignments_project_status
    ON project_assignments (project_id, status);

CREATE TABLE certificates (
    certificate_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    enrollment_id bigint NOT NULL REFERENCES enrollments(enrollment_id) ON DELETE RESTRICT,
    certificate_number text NOT NULL UNIQUE,
    certificate_type text NOT NULL,
    issued_at timestamptz NOT NULL,
    document_uri text,
    replaces_certificate_id bigint REFERENCES certificates(certificate_id) ON DELETE RESTRICT,
    issued_by bigint NOT NULL REFERENCES admins(admin_id) ON DELETE RESTRICT,
    created_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
    CONSTRAINT ck_certificates_number_not_blank CHECK (length(btrim(certificate_number)) > 0),
    CONSTRAINT ck_certificates_type_not_blank CHECK (length(btrim(certificate_type)) > 0),
    CONSTRAINT ck_certificates_not_self_replacement CHECK (
        replaces_certificate_id IS NULL OR replaces_certificate_id <> certificate_id
    ),
    CONSTRAINT uq_certificates_id_enrollment UNIQUE (certificate_id, enrollment_id)
);
CREATE INDEX ix_certificates_enrollment_issued
    ON certificates (enrollment_id, issued_at DESC);
CREATE INDEX ix_certificates_replaces
    ON certificates (replaces_certificate_id) WHERE replaces_certificate_id IS NOT NULL;

CREATE TABLE certificate_events (
    certificate_event_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    certificate_id bigint NOT NULL REFERENCES certificates(certificate_id) ON DELETE RESTRICT,
    event_type text NOT NULL,
    related_certificate_id bigint REFERENCES certificates(certificate_id) ON DELETE RESTRICT,
    occurred_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
    reason text NOT NULL,
    recorded_by bigint NOT NULL REFERENCES admins(admin_id) ON DELETE RESTRICT,
    created_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
    CONSTRAINT ck_certificate_events_type CHECK (
        event_type IN ('replaced', 'revoked', 'corrected')
    ),
    CONSTRAINT ck_certificate_events_not_self_related CHECK (
        related_certificate_id IS NULL OR related_certificate_id <> certificate_id
    ),
    CONSTRAINT ck_certificate_events_reason CHECK (length(btrim(reason)) > 0),
    CONSTRAINT ck_certificate_events_related CHECK (
        (event_type = 'replaced' AND related_certificate_id IS NOT NULL)
        OR (event_type IN ('revoked', 'corrected') AND related_certificate_id IS NULL)
    )
);
CREATE INDEX ix_certificate_events_certificate_time
    ON certificate_events (certificate_id, occurred_at DESC, certificate_event_id DESC);
CREATE UNIQUE INDEX ux_certificate_events_one_terminal_state
    ON certificate_events (certificate_id)
    WHERE event_type IN ('replaced', 'revoked');

CREATE TABLE audit_logs (
    audit_log_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    actor_admin_id bigint REFERENCES admins(admin_id) ON DELETE RESTRICT,
    action text NOT NULL,
    target_type text,
    target_id bigint,
    outcome text NOT NULL DEFAULT 'success',
    occurred_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
    request_id uuid,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    CONSTRAINT ck_audit_action_not_blank CHECK (length(btrim(action)) > 0),
    CONSTRAINT ck_audit_outcome CHECK (outcome IN ('success', 'failure', 'denied')),
    CONSTRAINT ck_audit_metadata_object CHECK (jsonb_typeof(metadata) = 'object')
);
CREATE INDEX ix_audit_logs_time ON audit_logs (occurred_at DESC, audit_log_id DESC);
CREATE INDEX ix_audit_logs_target_time
    ON audit_logs (target_type, target_id, occurred_at DESC)
    WHERE target_type IS NOT NULL AND target_id IS NOT NULL;
CREATE INDEX ix_audit_logs_actor_time
    ON audit_logs (actor_admin_id, occurred_at DESC)
    WHERE actor_admin_id IS NOT NULL;

-- Fee terms are immutable except that a current term may be closed once.
CREATE FUNCTION guard_enrollment_fee_term()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = internship_management, pg_temp
AS $$
DECLARE
    v_program_id bigint;
    v_paid numeric(14, 2);
    v_adjustment_total numeric(14, 2);
BEGIN
    IF TG_OP = 'UPDATE' THEN
        PERFORM 1 FROM enrollments
         WHERE enrollment_id = OLD.enrollment_id FOR UPDATE;
        IF OLD.effective_to IS NOT NULL
           OR NEW.effective_to IS NULL
           OR NEW.effective_to <= OLD.effective_from
           OR ROW(NEW.enrollment_id, NEW.fee_structure_id, NEW.agreed_amount,
                  NEW.currency, NEW.effective_from, NEW.reason, NEW.created_by,
                  NEW.created_at)
              IS DISTINCT FROM
              ROW(OLD.enrollment_id, OLD.fee_structure_id, OLD.agreed_amount,
                  OLD.currency, OLD.effective_from, OLD.reason, OLD.created_by,
                  OLD.created_at) THEN
            RAISE EXCEPTION 'Fee terms are immutable; only the current term may be closed';
        END IF;
        RETURN NEW;
    END IF;

    SELECT program_id INTO v_program_id
      FROM enrollments WHERE enrollment_id = NEW.enrollment_id FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Enrollment % does not exist', NEW.enrollment_id;
    END IF;

    IF NEW.fee_structure_id IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM fee_structures fs
         WHERE fs.fee_structure_id = NEW.fee_structure_id
           AND fs.program_id = v_program_id
    ) THEN
        RAISE EXCEPTION 'Fee structure must belong to the enrollment program';
    END IF;

    IF EXISTS (
        SELECT 1 FROM enrollment_fee_terms t
         WHERE t.enrollment_id = NEW.enrollment_id
           AND tstzrange(t.effective_from, t.effective_to, '[)')
               && tstzrange(NEW.effective_from, NEW.effective_to, '[)')
    ) THEN
        RAISE EXCEPTION 'Enrollment fee-term ranges may not overlap';
    END IF;

        SELECT COALESCE(SUM(
                CASE WHEN adjustment_type = 'fee_increase' THEN amount ELSE -amount END
        ), 0) INTO v_adjustment_total
            FROM fee_adjustments WHERE enrollment_id = NEW.enrollment_id;
        SELECT COALESCE(SUM(net_amount), 0) INTO v_paid
            FROM v_payment_status WHERE enrollment_id = NEW.enrollment_id;

        IF NEW.agreed_amount + v_adjustment_total < v_paid THEN
        RAISE EXCEPTION 'New fee amount cannot be less than net payments already received';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER trg_fee_terms_guard_insert
    BEFORE INSERT ON enrollment_fee_terms
    FOR EACH ROW EXECUTE FUNCTION guard_enrollment_fee_term();
CREATE TRIGGER trg_fee_terms_guard_update
    BEFORE UPDATE ON enrollment_fee_terms
    FOR EACH ROW EXECUTE FUNCTION guard_enrollment_fee_term();

CREATE FUNCTION reject_immutable_row_change()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = internship_management, pg_temp
AS $$
BEGIN
    RAISE EXCEPTION '% rows are append-only and cannot be updated or deleted', TG_TABLE_NAME;
END;
$$;
CREATE TRIGGER trg_fee_terms_no_delete
    BEFORE DELETE ON enrollment_fee_terms
    FOR EACH ROW EXECUTE FUNCTION reject_immutable_row_change();

-- A committed enrollment must have one current fee term. Create enrollment and its
-- initial fee term in the same transaction; the deferred check runs at commit.
CREATE FUNCTION require_current_fee_term()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = internship_management, pg_temp
AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM enrollment_fee_terms
         WHERE enrollment_id = NEW.enrollment_id AND effective_to IS NULL
    ) THEN
        RAISE EXCEPTION 'Enrollment % must have a current fee term before commit',
            NEW.enrollment_id;
    END IF;
    RETURN NULL;
END;
$$;
CREATE CONSTRAINT TRIGGER ct_enrollment_requires_fee_term
    AFTER INSERT ON enrollments
    DEFERRABLE INITIALLY DEFERRED
    FOR EACH ROW EXECUTE FUNCTION require_current_fee_term();
CREATE CONSTRAINT TRIGGER ct_fee_terms_require_current
    AFTER INSERT OR UPDATE ON enrollment_fee_terms
    DEFERRABLE INITIALLY DEFERRED
    FOR EACH ROW EXECUTE FUNCTION require_current_fee_term();

CREATE FUNCTION guard_fee_adjustment_insert()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = internship_management, pg_temp
AS $$
DECLARE
    v_fee numeric(14, 2);
    v_net_paid numeric(14, 2);
    v_adjustments numeric(14, 2);
    v_effect numeric(14, 2);
BEGIN
    PERFORM 1 FROM enrollments
     WHERE enrollment_id = NEW.enrollment_id FOR UPDATE;
    SELECT agreed_amount INTO v_fee
      FROM enrollment_fee_terms
     WHERE enrollment_id = NEW.enrollment_id AND effective_to IS NULL;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Enrollment has no current fee term';
    END IF;
    SELECT COALESCE(SUM(
        CASE WHEN adjustment_type = 'fee_increase' THEN amount ELSE -amount END
    ), 0) INTO v_adjustments
      FROM fee_adjustments WHERE enrollment_id = NEW.enrollment_id;
    SELECT COALESCE(SUM(net_amount), 0) INTO v_net_paid
      FROM v_payment_status WHERE enrollment_id = NEW.enrollment_id;
    v_effect := CASE WHEN NEW.adjustment_type = 'fee_increase' THEN NEW.amount ELSE -NEW.amount END;
    IF v_fee + v_adjustments + v_effect < 0
       OR v_fee + v_adjustments + v_effect < v_net_paid THEN
        RAISE EXCEPTION 'Fee adjustment cannot reduce the effective fee below net payments';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER trg_fee_adjustments_guard_insert
    BEFORE INSERT ON fee_adjustments
    FOR EACH ROW EXECUTE FUNCTION guard_fee_adjustment_insert();
CREATE TRIGGER trg_fee_adjustments_immutable
    BEFORE UPDATE OR DELETE ON fee_adjustments
    FOR EACH ROW EXECUTE FUNCTION reject_immutable_row_change();

-- Locking the enrollment serializes receipt inserts, fee changes, and refunds for
-- that enrollment. This prevents concurrent transactions from exceeding its fee.
CREATE FUNCTION guard_payment_insert()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = internship_management, pg_temp
AS $$
DECLARE
    v_fee numeric(14, 2);
    v_paid numeric(14, 2);
    v_adjustment_total numeric(14, 2);
BEGIN
    PERFORM 1 FROM enrollments
     WHERE enrollment_id = NEW.enrollment_id FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Enrollment % does not exist', NEW.enrollment_id;
    END IF;

    SELECT agreed_amount INTO v_fee
      FROM enrollment_fee_terms
     WHERE enrollment_id = NEW.enrollment_id AND effective_to IS NULL;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Enrollment % has no current fee term', NEW.enrollment_id;
    END IF;

        SELECT COALESCE(SUM(
                CASE WHEN adjustment_type = 'fee_increase' THEN amount ELSE -amount END
        ), 0) INTO v_adjustment_total
            FROM fee_adjustments WHERE enrollment_id = NEW.enrollment_id;
        SELECT COALESCE(SUM(net_amount), 0) INTO v_paid
            FROM v_payment_status WHERE enrollment_id = NEW.enrollment_id;

        IF NEW.amount > v_fee + v_adjustment_total - v_paid THEN
        RAISE EXCEPTION 'Payment exceeds enrollment balance (balance %, attempted %)',
                        v_fee + v_adjustment_total - v_paid, NEW.amount;
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER trg_payments_guard_insert
    BEFORE INSERT ON payments
    FOR EACH ROW EXECUTE FUNCTION guard_payment_insert();
CREATE TRIGGER trg_payments_immutable
    BEFORE UPDATE OR DELETE ON payments
    FOR EACH ROW EXECUTE FUNCTION reject_immutable_row_change();

CREATE FUNCTION guard_payment_adjustment_insert()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = internship_management, pg_temp
AS $$
DECLARE
    v_enrollment_id bigint;
    v_payment_amount numeric(14, 2);
    v_adjusted numeric(14, 2);
BEGIN
    SELECT enrollment_id INTO v_enrollment_id
      FROM payments WHERE payment_id = NEW.payment_id;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Payment % does not exist', NEW.payment_id;
    END IF;

    PERFORM 1 FROM enrollments
     WHERE enrollment_id = v_enrollment_id FOR UPDATE;
    SELECT amount INTO v_payment_amount
            FROM payments WHERE payment_id = NEW.payment_id;

    SELECT COALESCE(SUM(amount), 0) INTO v_adjusted
      FROM payment_adjustments WHERE payment_id = NEW.payment_id;

    IF NEW.amount > v_payment_amount - v_adjusted THEN
        RAISE EXCEPTION 'Refund/reversal exceeds the remaining payment amount';
    END IF;
    IF NEW.adjustment_type = 'reversal'
       AND NEW.amount <> v_payment_amount - v_adjusted THEN
        RAISE EXCEPTION 'A reversal must reverse the entire remaining payment amount';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER trg_payment_adjustments_guard_insert
    BEFORE INSERT ON payment_adjustments
    FOR EACH ROW EXECUTE FUNCTION guard_payment_adjustment_insert();
CREATE TRIGGER trg_payment_adjustments_immutable
    BEFORE UPDATE OR DELETE ON payment_adjustments
    FOR EACH ROW EXECUTE FUNCTION reject_immutable_row_change();

CREATE FUNCTION guard_certificate_insert()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = internship_management, pg_temp
AS $$
DECLARE
    v_old_enrollment_id bigint;
    v_old_type text;
BEGIN
    PERFORM 1 FROM enrollments
     WHERE enrollment_id = NEW.enrollment_id FOR UPDATE;

    IF NEW.replaces_certificate_id IS NOT NULL THEN
        SELECT enrollment_id, certificate_type
          INTO v_old_enrollment_id, v_old_type
          FROM certificates
         WHERE certificate_id = NEW.replaces_certificate_id;
        IF NOT FOUND THEN
            RAISE EXCEPTION 'Certificate being replaced does not exist';
        END IF;
        IF v_old_enrollment_id <> NEW.enrollment_id OR v_old_type <> NEW.certificate_type THEN
            RAISE EXCEPTION 'Replacement must have the same enrollment and certificate type';
        END IF;
        IF EXISTS (
            SELECT 1 FROM certificate_events
             WHERE certificate_id = NEW.replaces_certificate_id
               AND event_type IN ('replaced', 'revoked')
        ) THEN
            RAISE EXCEPTION 'A replaced or revoked certificate cannot be replaced again';
        END IF;
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER trg_certificates_guard_insert
    BEFORE INSERT ON certificates
    FOR EACH ROW EXECUTE FUNCTION guard_certificate_insert();
CREATE TRIGGER trg_certificates_immutable
    BEFORE UPDATE OR DELETE ON certificates
    FOR EACH ROW EXECUTE FUNCTION reject_immutable_row_change();

CREATE FUNCTION guard_certificate_event_insert()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = internship_management, pg_temp
AS $$
DECLARE
    v_enrollment_id bigint;
    v_related_enrollment_id bigint;
    v_replacement_source bigint;
BEGIN
    SELECT enrollment_id INTO v_enrollment_id
      FROM certificates WHERE certificate_id = NEW.certificate_id;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Certificate % does not exist', NEW.certificate_id;
    END IF;

    PERFORM 1 FROM enrollments
     WHERE enrollment_id = v_enrollment_id FOR UPDATE;

    IF NEW.related_certificate_id IS NOT NULL THEN
        SELECT enrollment_id, replaces_certificate_id
          INTO v_related_enrollment_id, v_replacement_source
          FROM certificates WHERE certificate_id = NEW.related_certificate_id;
        IF NOT FOUND OR v_related_enrollment_id <> v_enrollment_id THEN
            RAISE EXCEPTION 'Related certificate must exist and belong to the same enrollment';
        END IF;
          IF NEW.event_type = 'replaced'
              AND v_replacement_source IS DISTINCT FROM NEW.certificate_id THEN
            RAISE EXCEPTION 'Replacement certificate must reference the certificate being replaced';
        END IF;
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER trg_certificate_events_guard_insert
    BEFORE INSERT ON certificate_events
    FOR EACH ROW EXECUTE FUNCTION guard_certificate_event_insert();
CREATE TRIGGER trg_certificate_events_immutable
    BEFORE UPDATE OR DELETE ON certificate_events
    FOR EACH ROW EXECUTE FUNCTION reject_immutable_row_change();

CREATE FUNCTION require_replacement_event()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = internship_management, pg_temp
AS $$
BEGIN
    IF NEW.replaces_certificate_id IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM certificate_events
         WHERE certificate_id = NEW.replaces_certificate_id
           AND related_certificate_id = NEW.certificate_id
           AND event_type = 'replaced'
    ) THEN
        RAISE EXCEPTION 'Replacement certificate requires a matching replacement event';
    END IF;
    RETURN NULL;
END;
$$;
CREATE CONSTRAINT TRIGGER ct_certificate_replacement_event
    AFTER INSERT ON certificates
    DEFERRABLE INITIALLY DEFERRED
    FOR EACH ROW EXECUTE FUNCTION require_replacement_event();

CREATE TRIGGER trg_audit_logs_immutable
    BEFORE UPDATE OR DELETE ON audit_logs
    FOR EACH ROW EXECUTE FUNCTION reject_immutable_row_change();

CREATE VIEW v_payment_status AS
SELECT
    p.payment_id,
    p.enrollment_id,
    p.idempotency_key,
    p.amount,
    p.currency,
    p.paid_at,
    p.payment_method,
    p.payment_reference,
    p.recorded_by,
    p.created_at,
    COALESCE(a.adjusted_amount, 0)::numeric(14, 2) AS adjusted_amount,
    (p.amount - COALESCE(a.adjusted_amount, 0))::numeric(14, 2) AS net_amount,
    CASE
        WHEN COALESCE(a.reversed_amount, 0) > 0 THEN 'reversed'
        WHEN COALESCE(a.refunded_amount, 0) >= p.amount THEN 'refunded'
        WHEN COALESCE(a.refunded_amount, 0) > 0 THEN 'partially_refunded'
        ELSE 'posted'
    END AS derived_status
FROM payments p
LEFT JOIN (
    SELECT
        payment_id,
        SUM(amount) AS adjusted_amount,
        SUM(amount) FILTER (WHERE adjustment_type = 'refund') AS refunded_amount,
        SUM(amount) FILTER (WHERE adjustment_type = 'reversal') AS reversed_amount
    FROM payment_adjustments
    GROUP BY payment_id
) a ON a.payment_id = p.payment_id;

CREATE VIEW v_enrollment_balances AS
SELECT
    e.enrollment_id,
    e.enrollment_number,
    e.student_id,
    e.program_id,
    e.batch_id,
    e.status AS enrollment_status,
    ft.fee_term_id,
    ft.agreed_amount AS fee_amount,
    ft.currency,
    COALESCE(fa.adjustments_total, 0)::numeric(14, 2) AS adjustments_total,
    GREATEST(ft.agreed_amount + COALESCE(fa.adjustments_total, 0), 0)::numeric(14, 2)
        AS effective_fee,
    COALESCE(pt.net_paid, 0)::numeric(14, 2) AS net_paid,
    GREATEST(
        ft.agreed_amount + COALESCE(fa.adjustments_total, 0) - COALESCE(pt.net_paid, 0),
        0
    )::numeric(14, 2)
        AS pending_balance
FROM enrollments e
JOIN enrollment_fee_terms ft
  ON ft.enrollment_id = e.enrollment_id AND ft.effective_to IS NULL
LEFT JOIN (
        SELECT enrollment_id,
                     SUM(CASE WHEN adjustment_type = 'fee_increase' THEN amount ELSE -amount END)
                             AS adjustments_total
            FROM fee_adjustments
         GROUP BY enrollment_id
) fa ON fa.enrollment_id = e.enrollment_id
LEFT JOIN (
    SELECT enrollment_id, SUM(net_amount) AS net_paid
    FROM v_payment_status
    GROUP BY enrollment_id
) pt ON pt.enrollment_id = e.enrollment_id;

CREATE VIEW v_certificate_status AS
SELECT
    c.certificate_id,
    c.enrollment_id,
    c.certificate_number,
    c.certificate_type,
    c.issued_at,
    c.document_uri,
    c.replaces_certificate_id,
    c.issued_by,
    CASE
        WHEN terminal.event_type = 'revoked' THEN 'revoked'
        WHEN terminal.event_type = 'replaced' THEN 'replaced'
        ELSE 'issued'
    END AS derived_status,
    terminal.occurred_at AS terminal_event_at
FROM certificates c
LEFT JOIN LATERAL (
    SELECT ce.event_type, ce.occurred_at
    FROM certificate_events ce
    WHERE ce.certificate_id = c.certificate_id
      AND ce.event_type IN ('replaced', 'revoked')
    ORDER BY ce.occurred_at DESC, ce.certificate_event_id DESC
    LIMIT 1
) terminal ON true;

-- Safe local/test fixtures only. This intentionally inactive identity has no usable
-- password hash and must never be used as a production Admin account.
INSERT INTO admins (username, email, password_hash, is_active)
VALUES ('seed-disabled', 'seed-disabled@example.invalid', '!DISABLED-SEED-ONLY-NOT-A-HASH!', false);

INSERT INTO internship_programs (program_code, name, description, status, created_by)
SELECT 'SAMPLE-FASTAPI', 'Sample Backend Internship', 'Non-production fixture', 'active', admin_id
FROM admins WHERE username = 'seed-disabled';

INSERT INTO batches (program_id, batch_code, name, starts_on, ends_on, status, created_by)
SELECT p.program_id, 'SAMPLE-2026-01', 'Sample 2026 Cohort', DATE '2026-11-01', DATE '2027-01-31', 'active', a.admin_id
FROM internship_programs p CROSS JOIN admins a
WHERE p.program_code = 'SAMPLE-FASTAPI' AND a.username = 'seed-disabled';

INSERT INTO students (student_number, full_name, email, phone, status, created_by)
SELECT 'SAMPLE-STU-001', 'Sample Student', 'sample.student@example.invalid', NULL, 'active', admin_id
FROM admins WHERE username = 'seed-disabled';

INSERT INTO fee_structures (program_id, name, standard_amount, currency, is_active, created_by)
SELECT p.program_id, 'Standard Sample Fee', 10000.00, 'INR', true, a.admin_id
FROM internship_programs p CROSS JOIN admins a
WHERE p.program_code = 'SAMPLE-FASTAPI' AND a.username = 'seed-disabled';

INSERT INTO enrollments (
    enrollment_number, student_id, program_id, batch_id, status, starts_on, ends_on, created_by
)
SELECT 'SAMPLE-ENR-001', s.student_id, p.program_id, b.batch_id,
       'active', DATE '2026-11-01', DATE '2027-01-31', a.admin_id
FROM students s
JOIN internship_programs p ON p.program_code = 'SAMPLE-FASTAPI'
JOIN batches b ON b.program_id = p.program_id AND b.batch_code = 'SAMPLE-2026-01'
CROSS JOIN admins a
WHERE s.student_number = 'SAMPLE-STU-001' AND a.username = 'seed-disabled';

INSERT INTO enrollment_fee_terms (
    enrollment_id, fee_structure_id, agreed_amount, currency, effective_from, reason, created_by
)
SELECT e.enrollment_id, fs.fee_structure_id, 10000.00, 'INR',
       TIMESTAMPTZ '2026-10-16 09:00:00+00', 'Initial agreed enrollment fee', a.admin_id
FROM enrollments e
JOIN internship_programs p ON p.program_id = e.program_id
JOIN fee_structures fs ON fs.program_id = p.program_id AND fs.name = 'Standard Sample Fee'
CROSS JOIN admins a
WHERE e.enrollment_number = 'SAMPLE-ENR-001' AND a.username = 'seed-disabled';

INSERT INTO payments (
    enrollment_id, amount, currency, paid_at, payment_method, payment_reference, recorded_by
)
SELECT e.enrollment_id, 4000.00, 'INR', TIMESTAMPTZ '2026-10-16 10:00:00+00',
       'upi', 'SAMPLE-UPI-001', a.admin_id
FROM enrollments e CROSS JOIN admins a
WHERE e.enrollment_number = 'SAMPLE-ENR-001' AND a.username = 'seed-disabled';

INSERT INTO projects (project_code, name, description, status, created_by)
SELECT 'SAMPLE-PROJ-001', 'Sample Inventory API', 'Non-production fixture', 'active', admin_id
FROM admins WHERE username = 'seed-disabled';

INSERT INTO project_assignments (project_id, enrollment_id, status, assigned_by)
SELECT p.project_id, e.enrollment_id, 'in_progress', a.admin_id
FROM projects p
JOIN enrollments e ON e.enrollment_number = 'SAMPLE-ENR-001'
CROSS JOIN admins a
WHERE p.project_code = 'SAMPLE-PROJ-001' AND a.username = 'seed-disabled';

INSERT INTO certificates (
    enrollment_id, certificate_number, certificate_type, issued_at, issued_by
)
SELECT e.enrollment_id, 'SAMPLE-CERT-001', 'completion',
       TIMESTAMPTZ '2027-02-01 09:00:00+00', a.admin_id
FROM enrollments e CROSS JOIN admins a
WHERE e.enrollment_number = 'SAMPLE-ENR-001' AND a.username = 'seed-disabled';

INSERT INTO audit_logs (
    actor_admin_id, action, target_type, target_id, outcome, occurred_at, metadata
)
SELECT a.admin_id, 'seed_fixture_created', 'enrollment', e.enrollment_id,
       'success', transaction_timestamp(), '{"fixture": true}'::jsonb
FROM admins a CROSS JOIN enrollments e
WHERE a.username = 'seed-disabled' AND e.enrollment_number = 'SAMPLE-ENR-001';

COMMIT;