# Backend Setup

## Requirements

- Python 3.11 or newer
- PostgreSQL 14 or newer
- Windows PowerShell commands below can be adapted for another shell

## Local setup

From the repository root:

```powershell
cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

Edit `.env`: set `DATABASE_URL` for the runtime application, set `ADMIN_PROVISIONING_DATABASE_URL` for the bootstrap/reset CLI, and replace `JWT_SECRET_KEY` with a generated secret. The checked-in example reuses the local development DB principal for convenience only. In production, the API process needs only `DATABASE_URL`; run Alembic with a distinct TLS-protected `MIGRATION_DATABASE_URL`, and run the Admin CLI with a distinct TLS-protected `ADMIN_PROVISIONING_DATABASE_URL`. Never grant the runtime account ownership/DDL or Admin-provisioning privileges. Do not commit `.env`. For example, generate a secret in PowerShell with:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

The example database URL and key are placeholders, not production credentials.

## Migrations

Apply the versioned schema using `MIGRATION_DATABASE_URL` when configured (development/test falls back to `DATABASE_URL`):

```powershell
alembic upgrade head
alembic current
```

Migrations create only `internship_management.admins`, its authentication-version column, and shared Admin login-throttle buckets. They do not create future student or internship tables. Production must use Alembic migrations; the application never calls `metadata.create_all()` at startup.

## Provision the first Admin

There is no public registration route. Provision the first Admin through the operator CLI after applying the migration. The CLI uses `ADMIN_PROVISIONING_DATABASE_URL`; it does not fall back to the runtime URL. Bootstrap is allowed only while no Admin exists:

```powershell
python -m app.cli bootstrap-admin --username admin --email admin@example.com
```

The password is read interactively and hashed with Argon2. Do not pass passwords as command-line arguments or seed a usable production account.

Reset an existing Admin password through an interactive prompt. This increments the Admin authentication version and invalidates all previously issued access tokens:

```powershell
python -m app.cli reset-admin-password --username admin
```

## Run and verify

```powershell
uvicorn app.main:app --reload
```

- Liveness: `GET http://127.0.0.1:8000/api/v1/health/live`
- Database readiness: `GET http://127.0.0.1:8000/api/v1/health/ready`
- Admin login: `POST http://127.0.0.1:8000/api/v1/auth/login`
- Admin identity: `GET http://127.0.0.1:8000/api/v1/auth/me` with a bearer token
- Student collection: `GET http://127.0.0.1:8000/api/v1/students`
- OpenAPI docs are enabled only outside production: `http://127.0.0.1:8000/docs`

Access tokens are short-lived JWTs. Client sign-out must discard the token. A password reset increments the persisted Admin authentication version, revoking all prior tokens; deactivating an Admin blocks its tokens on their next protected request.

Run unit tests:

```powershell
pytest
```

PostgreSQL integration tests require a dedicated isolated database and `TEST_DATABASE_URL` in the process environment. They apply Alembic migrations to that database; do not point it at development or production data.

```powershell
$env:TEST_DATABASE_URL = "postgresql+psycopg://test_user:test_password@localhost:5432/internship_management_test"
pytest -m integration
```

Login throttling uses shared PostgreSQL buckets keyed by HMACed client addresses, so limits apply across workers without persisting raw IP addresses. The application does not trust arbitrary forwarded-IP headers; configure trusted proxy handling at deployment before operating behind a reverse proxy.

## Student API examples

Create a profile using the Admin bearer token. `created_by`, lifecycle timestamps, status, and archive metadata are server-controlled; unknown fields are rejected.

```http
POST /api/v1/students HTTP/1.1
Authorization: Bearer <admin-access-token>
Content-Type: application/json

{
  "student_number": "PT-2026-0042",
  "full_name": "Asha Patel",
  "email": "asha.patel@example.com",
  "phone": "+91 98765 43210"
}
```

```json
{
  "student_id": 42,
  "student_number": "PT-2026-0042",
  "full_name": "Asha Patel",
  "email": "asha.patel@example.com",
  "phone": "+91 98765 43210",
  "status": "active",
  "created_by": 1,
  "created_at": "2026-10-16T12:00:00Z",
  "updated_at": "2026-10-16T12:00:00Z",
  "archived_at": null
}
```

Search is case-insensitive substring matching over student number, name, email, and phone. Status may be `active`, `archived`, or `all`; page size is limited to 100.

```http
GET /api/v1/students?q=asha&status=active&page=1&page_size=20 HTTP/1.1
Authorization: Bearer <admin-access-token>
```

```json
{
  "items": [
    {
      "student_id": 42,
      "student_number": "PT-2026-0042",
      "full_name": "Asha Patel",
      "email": "asha.patel@example.com",
      "phone": "+91 98765 43210",
      "status": "active",
      "created_by": 1,
      "created_at": "2026-10-16T12:00:00Z",
      "updated_at": "2026-10-16T12:00:00Z",
      "archived_at": null
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20,
  "pages": 1
}
```

Retrieve with `GET /api/v1/students/{student_id}`. Update with `PATCH /api/v1/students/{student_id}` and a non-empty subset of editable fields, for example `{ "full_name": "Asha P. Patel" }`. Setting `status` to `archived` archives the record; setting it back to `active` restores it. There is intentionally no `DELETE` endpoint.

## Program, batch, and enrollment API examples

Create an active program and a batch. A null/omitted capacity means unlimited; active enrollments count against a configured capacity.

```http
POST /api/v1/programs HTTP/1.1
Authorization: Bearer <admin-access-token>
Content-Type: application/json

{
  "program_code": "PY-FASTAPI-01",
  "name": "FastAPI Internship",
  "description": "Backend internship cohort",
  "status": "active"
}
```

```json
{
  "program_id": 12,
  "program_code": "PY-FASTAPI-01",
  "name": "FastAPI Internship",
  "description": "Backend internship cohort",
  "status": "active",
  "created_by": 1,
  "created_at": "2026-10-16T12:00:00Z",
  "updated_at": "2026-10-16T12:00:00Z"
}
```

```http
POST /api/v1/batches HTTP/1.1
Authorization: Bearer <admin-access-token>
Content-Type: application/json

{
  "program_id": 12,
  "batch_code": "NOV-2026-A",
  "name": "November 2026 Cohort A",
  "starts_on": "2026-11-01",
  "ends_on": "2027-01-31",
  "capacity": 25
}
```

Enroll an active student in an active program and an eligible batch. The enrollment is created active; status changes go through the dedicated endpoint.

```http
POST /api/v1/enrollments HTTP/1.1
Authorization: Bearer <admin-access-token>
Content-Type: application/json

{
  "enrollment_number": "ENR-2026-0042",
  "student_id": 42,
  "program_id": 12,
  "batch_id": 18,
  "starts_on": "2026-11-01",
  "ends_on": "2027-01-31",
  "agreed_fee_amount": "10000.00",
  "fee_reason": "Approved initial fee"
}
```

```json
{
  "enrollment_id": 73,
  "enrollment_number": "ENR-2026-0042",
  "student_id": 42,
  "program_id": 12,
  "batch_id": 18,
  "status": "active",
  "starts_on": "2026-11-01",
  "ends_on": "2027-01-31",
  "created_by": 1,
  "created_by": 1,
  "created_at": "2026-10-16T12:00:00Z",
  "updated_at": "2026-10-16T12:00:00Z"
}
```

List enrollments with `GET /api/v1/enrollments?student_id=42&program_id=12&batch_id=18&status=active&page=1&page_size=20`; search by enrollment number, student number, or name with `q`. Get a batch roster with `GET /api/v1/batches/18/roster`. Complete an enrollment with `PATCH /api/v1/enrollments/73/status` and `{ "status": "completed" }`. Current allowed enrollment transitions are active to completed/withdrawn/cancelled; terminal enrollment statuses cannot be reactivated. Student/program/batch identity and enrollment dates are not editable after creation through these APIs, preserving the enrollment's original association. Program status transitions are draft to active/inactive, active to inactive, and inactive to active. Batch status transitions are planned to active/cancelled and active to completed/cancelled. Batch capacity is optional; only active enrollments consume a slot. No program, batch, or enrollment delete endpoint is provided.

## Finance, projects, and certificates

Each enrollment is created with an exact decimal `agreed_fee_amount`. Read its authoritative fee summary with `GET /api/v1/enrollments/{enrollment_id}/fees`; current fee terms and approved adjustments are available from `GET /api/v1/enrollments/{enrollment_id}/fee-terms` and `GET /api/v1/enrollments/{enrollment_id}/fee-adjustments`.

```http
POST /api/v1/enrollments/73/payments HTTP/1.1
Authorization: Bearer <admin-access-token>
Idempotency-Key: 08e1aa83-dcdf-41d9-91d6-4b299ed36bf3
Content-Type: application/json

{
  "amount": "2500.00",
  "payment_method": "upi",
  "payment_reference": "UPI-2026-00073"
}
```

```json
{
  "payment_id": 201,
  "enrollment_id": 73,
  "amount": "2500.00",
  "currency": "INR",
  "paid_at": "2026-10-16T12:00:00Z",
  "payment_method": "upi",
  "payment_reference": "UPI-2026-00073",
  "recorded_by": 1,
  "created_at": "2026-10-16T12:00:00Z",
  "adjusted_amount": "0.00",
  "net_amount": "2500.00",
  "derived_status": "posted"
}
```

Repeat the same request with the same `Idempotency-Key` to receive the original payment with HTTP 200; reusing that key with different payment data returns HTTP 409. Payment history is paginated at `GET /api/v1/enrollments/{enrollment_id}/payments`. A fee discount/increase requires an explicit adjustment type, amount, reason, and UUID idempotency key; the authenticated Admin is recorded as approver. Refunds and reversals use `POST /api/v1/payments/{payment_id}/adjustments`; refunds may be partial, while reversal must neutralize the remaining receipt.

Assign a project with `POST /api/v1/enrollments/{enrollment_id}/projects` and `{ "project_id": 9 }`. Update assignment progress at `PATCH /api/v1/project-assignments/{assignment_id}/status` with `in_progress`, `completed`, or `cancelled`; completion is timestamped and audited.

Issue a certificate with `POST /api/v1/certificates` using `enrollment_id`, `certificate_number`, and `certificate_type`. Issued rows cannot be updated or deleted. Corrections are recorded as events; replacement issues a new certificate and links it to the original; revocation is a separate traceable event. The report is `GET /api/v1/certificates?status=issued&page=1&page_size=20`, with `status` supporting `issued`, `replaced`, `revoked`, or `all`.
