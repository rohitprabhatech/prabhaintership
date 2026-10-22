# Database guide

## Engine and source of truth

The application uses **Oracle MySQL**, through SQLAlchemy's `mysql+pymysql` driver. The configured database was verified as **MySQL 9.5.0** at Alembic revision `0009` (`head`). The supported minimum is **MySQL 8.0.16**, which enforces the `CHECK` constraints used by the application. Tables use InnoDB; application timestamps are stored as UTC `DATETIME` values.

Alembic migrations and SQLAlchemy models are authoritative for application setup and schema changes. `schema.sql` is a MySQL reference baseline for a separate, empty database. It is not an Alembic migration, contains no sample or Admin data, and must never be run against an existing or production database. It creates a conspicuously named `internship_management_schema_template` database and will fail if that database already exists.

## Main tables and relationships

- `admins` contains the authorized administrator accounts; `admin_login_throttles` stores hashed login-rate-limit keys. Neither table should be populated with example credentials.
- `students` stores student profiles. A student can have multiple historical `enrollments`.
- `internship_programs` has many `batches`. Every batch belongs to one program.
- Each `enrollment` links one student, one program, and one required batch. A composite foreign key ensures the selected batch belongs to the enrollment's program. A generated unique key prevents duplicate active enrollments for the same student/program/batch while preserving historical enrollments.
- `fee_structures` are program-level templates. `enrollment_fee_terms` records the agreed fee over time; a new term closes the previous term rather than overwriting it. `fee_adjustments` records discounts and increases separately.
- `payments` are append-only receipts. `payment_adjustments` records partial refunds and full reversals separately. Idempotency keys protect payment and adjustment creation from duplicate requests. The balance views derive the effective fee, net paid amount, and pending balance from those records.
- `projects` are linked to students through `project_assignments`, which reference the applicable enrollment. `certificates` and `certificate_events` are likewise enrollment-linked and preserve replacement, correction, and revocation history.
- `audit_logs` preserve administrative actions. Foreign keys use restrictive deletion rules to protect history.

The current-fee generated unique key enforces **at most one** current term for an enrollment. MySQL does not support deferred constraint triggers, so the database cannot independently require that at least one current term exist at commit. Application services create an enrollment and its initial fee term in one transaction and retain a current term during revisions. Direct SQL writes to enrollment and finance tables are unsupported; use the application services.

Financial values use `DECIMAL(14,2)` in INR. Database checks and triggers enforce positive amounts, fee-term range consistency, fee-structure/program matching, payment caps, refund limits, full-reversal amounts, append-only history, and certificate event consistency. The application locks the enrollment while changing its financial ledger, validates business rules, records audit data, and commits the operation atomically. `v_payment_status`, `v_enrollment_balances`, and `v_certificate_status` are derived views, not editable balance stores.

## Safe local setup

1. Install the backend dependencies and run a local Oracle MySQL 8.0.16+ server. Create a **new empty development database** with a developer-owned account; do not point local work at the existing `internship_management` database.
2. Copy `backend/.env.example` to `backend/.env` and set local-only values. The application uses `APP_ENV`, `APP_NAME`, `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_SSL_CA`, `JWT_SECRET_KEY`, `JWT_ISSUER`, `JWT_AUDIENCE`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `CORS_ORIGINS`, and `AUTH_RATE_LIMIT_ATTEMPTS`, `AUTH_RATE_LIMIT_WINDOW_SECONDS`, and `AUTH_RATE_LIMIT_BLOCK_SECONDS`.
3. For migrations, configure the separate `MIGRATION_DB_HOST`, `MIGRATION_DB_PORT`, `MIGRATION_DB_NAME`, `MIGRATION_DB_USER`, `MIGRATION_DB_PASSWORD`, and optional `MIGRATION_DB_SSL_CA` values. `MIGRATION_DATABASE_URL` is also supported, but must use the `mysql+pymysql` driver. Keep the migration database name pointed at the same isolated local development database.
4. From `backend`, apply the normal application migrations:

   ```powershell
   .\.venv\Scripts\python.exe -m alembic upgrade head
   .\.venv\Scripts\python.exe -m alembic current
   ```

   `alembic current` should report the current head revision. Provision a local Admin through the application's supported CLI only after migration; do not insert an Admin or a password hash from SQL.
5. To run database-backed tests, create another isolated MySQL database whose name ends in `_test`, then set `TEST_DATABASE_URL` to its `mysql+pymysql` connection string. The test configuration rejects a non-test database name. Never use the normal development or production database for tests.

Do not run `database/schema.sql` as part of the migration setup above. The reference baseline exists for schema review and team handover; it does not create Alembic migration history. If it is intentionally used to inspect a fresh disposable database, use only the dedicated template database it creates and do not then run Alembic against that database.

## Verifying model and database agreement

- From `backend`, run `.\.venv\Scripts\python.exe -m alembic check` to check for ORM table/column changes that lack a migration, and `.\.venv\Scripts\python.exe -m alembic current` to inspect the applied revision.
- Run `.\.venv\Scripts\python.exe -m app.cli verify-db` to verify the configured database connection and server.
- ORM autogeneration does not validate custom views or triggers. Compare those definitions with migrations `0007` and `0008` and with `database/schema.sql`; review any proposed migration before applying it.

The migration environment restricts autogeneration to the configured application database. MySQL may reflect a foreign key within the currently selected database without an explicit schema prefix; Alembic normalizes that same-database qualification while still comparing the FK name, columns, and rules.

The baseline intentionally contains no fixtures or sample records. Use isolated test factories for automated tests and never seed placeholder Admin, student, payment, or certificate data into a shared database. If the reference file is intentionally executed, use the MySQL command-line client because its stored-program section uses MySQL `DELIMITER` directives.

Admin provisioning can use the optional `ADMIN_PROVISIONING_DB_HOST`, `ADMIN_PROVISIONING_DB_PORT`, `ADMIN_PROVISIONING_DB_NAME`, `ADMIN_PROVISIONING_DB_USER`, `ADMIN_PROVISIONING_DB_PASSWORD`, and `ADMIN_PROVISIONING_DB_SSL_CA` settings. Production secrets, database users and grants, network access, backups, TLS certificates, and deployment configuration are managed separately. Do not copy local credentials into source control or use a baseline script to upgrade a populated database. Existing databases must be changed only through reviewed, forward-only Alembic migrations after a schema and data preflight.
