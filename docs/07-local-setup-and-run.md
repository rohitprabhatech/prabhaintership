# Local Setup and Run

## Prerequisites

- Windows 10/11, Python 3.11+, MySQL 8+ (the verified local server was MySQL 9.5.0), and Node.js/npm.
- The `internship_management` database must already exist. Tables are managed by Alembic; do not create them manually.
- Keep the database password and JWT signing secret in the backend `.env`, not in source control or command history.

## Backend Environment

The application reads `backend/.env`. The local file already exists and the application successfully loaded it. Required database variable names are `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, and `DB_PASSWORD`; the URL is assembled with SQLAlchemy `URL.create()` and the `mysql+pymysql` driver.

`backend/.env.example` is a placeholder template. Do not replace the local `.env` with the example. `.env` is ignored by Git.

## Install Backend

From the repository root in PowerShell:

```powershell
cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

If `.venv` already exists, activate it rather than recreating it.

## Verify MySQL and Migrations

From `backend` with the virtual environment active:

```powershell
python -m app.cli verify-db
python -m alembic current
```

The verification command runs `SELECT 1`, reports the selected database and server version, and does not print the password or URL. Verified locally on 2026-10-21: the `MySQL95` service is running, and the application connects to `internship_management` on MySQL 9.5.0 at Alembic revision `0009`. Revision `0009` adds generated-identifier counters, student profile fields, program duration, global batch-code uniqueness, and mandatory enrollment batches. It performs read-only preflight checks and stops before DDL if enrollments lack a batch, reference a missing/wrong-program batch, or batch codes collide.

For a different database, first verify the configured target and current revision, create a backup and verify the dump completes, and review the migration preflight. Obtain explicit database-change approval before applying schema changes. From `backend`, the migration commands are:

```powershell
python -m alembic upgrade head
python -m alembic current
```

Expected application tables after revision `0009` also include `business_number_counters`, alongside `admins`, `admin_login_throttles`, `students`, `internship_programs`, `batches`, `enrollments`, `fee_structures`, `enrollment_fee_terms`, `fee_adjustments`, `payments`, `payment_adjustments`, `projects`, `project_assignments`, `certificates`, `certificate_events`, and `audit_logs`. Alembic also manages `alembic_version`; three MySQL views are `v_payment_status`, `v_enrollment_balances`, and `v_certificate_status`.

Inspect names without exposing row data:

```powershell
python -c "from app.config import get_settings; from sqlalchemy import create_engine, inspect; s=get_settings(); e=create_engine(s.database_url, connect_args=s.database_connect_args); i=inspect(e); print(sorted(i.get_table_names(schema=s.db_name))); print(sorted(i.get_view_names(schema=s.db_name))); e.dispose()"
```

`database/schema.sql`, `SRS.md`, and `docs/03-database-design.md` still describe PostgreSQL and are not executable MySQL migration scripts. The current backend and Alembic revisions use MySQL. Reconcile those draft documents before treating the database design as approved; use reviewed Alembic revisions for MySQL.

## Important Current Database State

Earlier QA work wrote test-generated data to `internship_management`. Read-only inspection found 42 active Admin accounts, none matching the requested `prabhatech` username/email at that time, and business/audit records reference Admin IDs. The replacement command has not yet been run, and these code/documentation changes do not modify account records. Review the database and obtain explicit authorization before changing accounts. Integration tests must use a separate QA schema as described below; never run them against `internship_management`.

For MySQL integration tests, provision a separate QA schema and set `APP_ENV=test`, `DB_NAME`, and `TEST_DATABASE_URL` before Python imports any `app` modules. Build URLs with SQLAlchemy `URL.create()` so special characters are encoded safely. Never use the development or production database for destructive/repeatable tests. Without `TEST_DATABASE_URL`, database-backed tests skip rather than connecting to the local application database.

## Admin Provisioning

There is no public Admin registration. For a first Admin in an empty database, bootstrap from `backend`:

```powershell
python -m app.cli bootstrap-admin --username <admin-identifier> --email <admin-email>
```

The command prompts for the password and confirmation interactively and stores an Argon2 hash. Do not put a password in the command line. It refuses to create a second Admin. To replace the existing Admin set with a newly authorized account, use this command only after reviewing the target database and receiving explicit authorization:

```powershell
python -m app.cli replace-admin --username prabhatech --email prabhatech@gmail.com
```

The CLI reports how many currently active Admin rows would be deactivated and how many already-inactive rows will be retained. It displays a confirmation phrase containing the active count and the new username (for example, `DEACTIVATE ALL 42 ACTIVE ADMINS AND CREATE PRABHATECH`). Type that exact phrase to continue; any mismatch cancels before prompting for the password. The password and confirmation are entered through hidden terminal prompts, never as command-line arguments. The command requires at least one active Admin and an unused username/email. It rechecks the active Admin count under a provisioning lock, creates and verifies the new Argon2 password hash, then inserts the replacement and deactivates the reviewed active Admin set in one transaction. Existing Admin rows are retained to preserve foreign-key references, audit history, and related business history; newly deactivated accounts have their `auth_version` incremented to invalidate existing access tokens. An audit event records the replacement.

On successful completion, the CLI reports the new account's username, email, active status, and number of deactivated Admins; it verifies the password through the application's authentication service without displaying the password or hash. You can also verify the identity without selecting a password hash:

```sql
SELECT username, email, is_active
FROM `internship_management`.`admins`
WHERE username = 'prabhatech';
```

If preflight, confirmation, validation, or a transactional database operation fails, no Admin rows are changed. If the CLI reports a failure during its post-commit authentication verification, do not rerun replacement: first use the read-only query above to inspect the new account, then recover only with explicit authorization. To reset a confirmed existing account:

```powershell
python -m app.cli reset-admin-password --username <admin-identifier>
```

The reset command also invalidates existing access tokens. MySQL credentials are not Admin login credentials.

To review identifiers without selecting password hashes, an authorized database owner can run this read-only query in MySQL:

```sql
SELECT username, is_active
FROM `internship_management`.`admins`
ORDER BY admin_id;
```

Do not assume any existing account is valid. The UI login URL is `http://localhost:5173/login`; API login is `POST http://127.0.0.1:8000/api/v1/auth/login`. After replacement, sign in to the UI with username `prabhatech` and the password entered at the hidden terminal prompt.

Swagger UI: `http://127.0.0.1:8000/docs` in development.

## Change Admin Password

Authenticated Admins can open **Change password** from the dashboard sidebar. The page requires the current password, a new password, and matching confirmation. Passwords must be 12-1024 characters; the new password must differ from the current password. The UI supports per-field reveal controls but does not persist entered passwords.

The frontend sends the bearer-authenticated request to `POST /api/v1/auth/change-password`:

```json
{
  "current_password": "entered securely in the form",
  "new_password": "entered securely in the form",
  "confirm_password": "entered securely in the form"
}
```

The API derives the Admin ID from the verified JWT, verifies the current Argon2 hash, updates only that Admin row, and writes a password-change audit event without password material. It applies the existing login throttling to current-password failures. There is no schema migration. On success, `auth_version` is incremented, invalidating the current and any other outstanding access tokens; the UI clears the session and requires signing in again with the new password. Invalid current password, mismatch, weak/reused password, expired session, and rate limiting return safe errors without echoing password values or hashes.

Run backend tests from `backend`:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pytest -q
```

Database-backed tests require `TEST_DATABASE_URL` to point to an isolated MySQL test schema. Do not run integration tests against the application database.

## Start the Application

Backend, from `backend`:

```powershell
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Frontend, in another PowerShell terminal from `frontend`:

```powershell
npm install
npm run dev -- --host 127.0.0.1
```

Vite's actual `dev` script serves at `http://localhost:5173` by default. The frontend defaults to API base `http://localhost:8000`; its API root is `/api/v1`. Backend CORS defaults to `http://localhost:5173`.

The backend command was verified on port 18080 because port 8000 was occupied during QA. A Vite server was verified on port 5174 because 5173 already had a listener. Neither existing process was stopped. If ports are still occupied, select free ports; set `VITE_API_BASE_URL` to the backend URL and add the frontend origin to `CORS_ORIGINS` in `backend/.env`.

## Tests and Current Results

Backend non-integration tests:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m pytest -q
```

Observed from a safe local test environment without `TEST_DATABASE_URL`: **24 passed, 27 skipped**, with one Starlette deprecation warning. The 27 database-backed tests skip unless an isolated `TEST_DATABASE_URL` and matching `DB_NAME` are supplied.

The full MySQL integration suite was run against an isolated QA schema and reported **51 passed, 2 warnings**. It must not be pointed at `internship_management`; see [`05-testing-report.md`](05-testing-report.md) for the schema name, defects corrected, and evidence.

Frontend tests:

```powershell
cd frontend
npm test -- --no-cache --reporter=dot
```

Observed: **3 test files passed, 20 tests passed**. `npm run build` also completed successfully. See [`05-testing-report.md`](05-testing-report.md) for evidence and remaining QA limitations.

## Troubleshooting

- **MySQL unreachable (2003):** start the local MySQL service and confirm it listens on port 3306; rerun `python -m app.cli verify-db`.
- **Access denied (1045):** check `DB_USER`/`DB_PASSWORD` in `backend/.env` and database grants. Do not paste credentials into issue reports.
- **Database not found (1049):** verify `DB_NAME=internship_management` and that the database exists; do not create tables manually.
- **Missing Python dependency:** activate `backend/.venv`, then run `python -m pip install -e ".[dev]"`.
- **Migration error:** check `python -m alembic current`, review the migration operations, and confirm the target database is local/non-production before applying. Never use `downgrade base` as troubleshooting on a database with data.
- **CORS error:** confirm the frontend origin matches `CORS_ORIGINS` in `backend/.env` and restart the API.
- **Authentication failure:** use the Admin UI `/login`; confirm the account identifier with the authorized owner. The CLI never reveals a stored password. A password reset requires explicit authorization.
- **Frontend cannot reach API:** set `VITE_API_BASE_URL=http://localhost:8000` in the frontend environment if overriding the default, then restart Vite. Do not put backend secrets in `VITE_*` variables.
- **Test database isolation:** set `APP_ENV=test`, `DB_NAME`, and `TEST_DATABASE_URL` before importing application modules; confirm the URL database matches the dedicated test schema and is not `internship_management`.
