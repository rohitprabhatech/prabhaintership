# Internship Management System API Reference

**Version:** 0.1  
**API base path:** `/api/v1`  
**Authentication:** Admin bearer token, except liveness/readiness and Admin login.

This reference documents the currently implemented FastAPI routes. It is based on the route and Pydantic schema definitions in `backend/app`. OpenAPI is available at `/docs` in non-production environments; production disables `/docs`, `/redoc`, and `/openapi.json`.

## Access and Response Conventions

- All student, program, batch, enrollment, finance, project, project-assignment, and certificate endpoints require `Authorization: Bearer <access_token>`.
- `POST /api/v1/auth/login`, `GET /api/v1/health/live`, and `GET /api/v1/health/ready` are public operational/authentication routes. Readiness returns only whether the database is available.
- Business endpoints do not provide public registration, student authentication, or delete operations.
- Successful create operations normally return `201 Created`; reads and updates return `200 OK`. Idempotent replays of payment or fee/payment adjustment writes return `200 OK` with the original resource.
- Query pagination defaults to `page=1&page_size=20`; maximum page size is 100. Paged responses contain `items`, `total`, `page`, `page_size`, and `pages`.
- Validation errors return `422`; missing resources return `404`; duplicate, lifecycle, balance, and idempotency conflicts return `409`; missing/invalid authentication returns `401`; unexpected failures return a sanitized `500` response.
- Monetary requests and responses use decimal values serialized as strings, with two fractional digits and currency `INR`. Do not send JSON floating-point values for money; send strings such as `"2500.00"`.
- Payment, fee-adjustment, and payment-adjustment `POST` requests require an `Idempotency-Key` header containing a UUID.

Error response shape:

```json
{
  "type": "about:blank",
  "title": "Request failed",
  "status": 409,
  "code": "overpayment_rejected",
  "request_id": "b6ebc4d1-0648-4c76-a63d-0fe0644b1f5d"
}
```

Validation errors use `code: "validation_error"` and add an `errors` array containing `location`, `message`, and `code`; submitted values are not echoed.

## Health

| Method and path | Access | Purpose | Response |
| --- | --- | --- | --- |
| `GET /api/v1/health/live` | Public | Process liveness | `200 {"status":"ok"}` |
| `GET /api/v1/health/ready` | Public | Database readiness | `200 {"status":"ready","database":"available"}` or sanitized `503` |

## Admin Authentication

| Method and path | Access | Request | Response |
| --- | --- | --- | --- |
| `POST /api/v1/auth/login` | Public | `LoginRequest` | `200 LoginResponse`, `401` invalid credentials, `429` rate limited |
| `GET /api/v1/auth/me` | Admin | None | `200 AdminPublic`, `401` invalid/expired token |

`LoginRequest`: `username` (string, 1-128), `password` (string, 1-1024).  
`LoginResponse`: `access_token`, `token_type` (`bearer`), `expires_in` (seconds), `admin`.  
`AdminPublic`: `admin_id`, `username`, `email`, `is_active`.

Access tokens are short-lived JWTs. Admin password reset increments `auth_version`, invalidating existing tokens. There is no server-side logout/revocation endpoint; clients discard tokens on sign-out. Admin bootstrap and reset are operator CLI operations, not HTTP routes.

## Students

| Method and path | Access | Operation |
| --- | --- | --- |
| `POST /api/v1/students` | Admin | Create a student |
| `GET /api/v1/students` | Admin | List/search/filter students with pagination |
| `GET /api/v1/students/{student_id}` | Admin | Retrieve a student profile |
| `PATCH /api/v1/students/{student_id}` | Admin | Update editable fields or archive/reactivate |

`StudentCreate`: `student_number`, `full_name`, optional `email`, optional `phone`. Status, creator, and timestamps are server-controlled.  
`StudentUpdate`: non-empty subset of `student_number`, `full_name`, `email`, `phone`, `status`.  
List query: `page`, `page_size`, optional `q` (case-insensitive substring search across number/name/email/phone), `status` (`active`, `archived`, `all`; defaults to `active`).  
`StudentResponse`: `student_id`, `student_number`, `full_name`, `email`, `phone`, `status`, `created_by`, `created_at`, `updated_at`, `archived_at`.

## Internship Programs

| Method and path | Access | Operation |
| --- | --- | --- |
| `POST /api/v1/programs` | Admin | Create a program |
| `GET /api/v1/programs` | Admin | List/search/filter programs with pagination |
| `GET /api/v1/programs/{program_id}` | Admin | Retrieve a program |
| `PATCH /api/v1/programs/{program_id}` | Admin | Update name, description, or status |

`ProgramCreate`: `program_code`, `name`, optional `description`, optional initial `status` (`draft` or `active`).  
`ProgramUpdate`: non-empty subset of `name`, `description`, `status` (`draft`, `active`, `inactive`).  
List query: `page`, `page_size`, optional `q` (program code/name), `status` (`draft`, `active`, `inactive`, `all`; defaults to `all`).  
`ProgramResponse`: `program_id`, `program_code`, `name`, `description`, `status`, `created_by`, `created_at`, `updated_at`.

## Batches

| Method and path | Access | Operation |
| --- | --- | --- |
| `POST /api/v1/batches` | Admin | Create a batch under an active program |
| `GET /api/v1/batches` | Admin | List/filter batches with pagination |
| `GET /api/v1/batches/{batch_id}` | Admin | Retrieve a batch |
| `PATCH /api/v1/batches/{batch_id}` | Admin | Update name, dates, capacity, or status |
| `GET /api/v1/batches/{batch_id}/roster` | Admin | Retrieve roster and active enrollment count |

`BatchCreate`: `program_id`, `batch_code`, `name`, `starts_on`, `ends_on`, optional positive `capacity` (null/omitted means unlimited), optional initial `status` (`planned` or `active`). End date must not precede start date.  
`BatchUpdate`: non-empty subset of `name`, `starts_on`, `ends_on`, `capacity`, `status`. Capacity cannot be reduced below active enrollment count; dates cannot exclude existing enrollments.  
List query: `page`, `page_size`, optional `program_id`, `status` (`planned`, `active`, `completed`, `cancelled`, `all`; defaults to `all`).  
`BatchResponse`: `batch_id`, `program_id`, `batch_code`, `name`, `starts_on`, `ends_on`, `capacity`, `status`, `created_by`, `created_at`, `updated_at`.  
`BatchRoster`: batch identity/dates/capacity, `active_enrollment_count`, and `students`. Each roster entry includes enrollment identity/status/dates and student identity/contact fields.

## Enrollments

| Method and path | Access | Operation |
| --- | --- | --- |
| `POST /api/v1/enrollments` | Admin | Enroll an active student in an active program and optional eligible batch; atomically records the initial fee term |
| `GET /api/v1/enrollments` | Admin | List/filter/search enrollments with pagination |
| `GET /api/v1/enrollments/{enrollment_id}` | Admin | Retrieve enrollment identity/status/history anchor |
| `PATCH /api/v1/enrollments/{enrollment_id}/status` | Admin | Apply an allowed status transition |

`EnrollmentCreate`: `enrollment_number`, `student_id`, `program_id`, optional `batch_id`, `starts_on`, optional `ends_on`, exact-decimal `agreed_fee_amount`, optional `fee_reason`. The initial fee term is inserted in the enrollment transaction.  
List query: `page`, `page_size`, optional `student_id`, `program_id`, `batch_id`, `q` (enrollment number/student number/name), `status` (`active`, `completed`, `withdrawn`, `cancelled`, `all`; defaults to `all`).  
`EnrollmentStatusUpdate`: `status`. Implemented transitions are `active` to `completed`, `withdrawn`, or `cancelled`; terminal states cannot be reactivated. Enrollment links/dates have no update endpoint and enrollments have no delete endpoint.

## Fees and Payments

| Method and path | Access | Operation |
| --- | --- | --- |
| `GET /api/v1/enrollments/{enrollment_id}/fees` | Admin | Read current authoritative fee summary |
| `GET /api/v1/enrollments/{enrollment_id}/fee-terms` | Admin | Read fee-term history |
| `POST /api/v1/enrollments/{enrollment_id}/fee-terms` | Admin | Close current term and create a new agreed term |
| `GET /api/v1/enrollments/{enrollment_id}/fee-adjustments` | Admin | Read approved discount/increase history |
| `POST /api/v1/enrollments/{enrollment_id}/fee-adjustments` | Admin | Approve an append-only fee discount/increase |
| `GET /api/v1/enrollments/{enrollment_id}/payments` | Admin | Read paginated payment/refund/reversal status history |
| `POST /api/v1/enrollments/{enrollment_id}/payments` | Admin | Record an installment against one enrollment |
| `GET /api/v1/payments/{payment_id}/adjustments` | Admin | Read refund/reversal events for a receipt |
| `POST /api/v1/payments/{payment_id}/adjustments` | Admin | Record a refund or full remaining-amount reversal |

`FeeTermCreate`: positive `agreed_amount` with at most two decimal places, `reason`.  
`FeeAdjustmentCreate`: `adjustment_type` (`discount` or `fee_increase`), positive `amount` to two decimal places, and `reason`. The authenticated Admin is stored as approver.  
`PaymentCreate`: positive `amount` to two decimal places, `payment_method` (`cash`, `bank_transfer`, `upi`, `card`, `cheque`, `other`), optional `payment_reference`, optional timezone-aware `paid_at`.  
`PaymentAdjustmentCreate`: `adjustment_type` (`refund` or `reversal`), positive `amount` to two decimal places, and `reason`. Reversal must equal the remaining receipt amount.  
`FeeSummary`: enrollment/fee-term IDs, `base_fee`, signed `adjustments_total`, `effective_fee`, `currency`, `net_paid`, `pending_balance`. Payment statuses are derived: `posted`, `partially_refunded`, `refunded`, `reversed`.

## Projects

| Method and path | Access | Operation |
| --- | --- | --- |
| `POST /api/v1/projects` | Admin | Create a project |
| `GET /api/v1/projects` | Admin | List projects with pagination/status filter |
| `GET /api/v1/projects/{project_id}` | Admin | Retrieve project definition |
| `POST /api/v1/enrollments/{enrollment_id}/projects` | Admin | Assign a project to an active enrollment |
| `GET /api/v1/project-assignments` | Admin | List/filter assignments with pagination |
| `PATCH /api/v1/project-assignments/{assignment_id}/status` | Admin | Update progress/completion state |

`ProjectCreate`: `project_code`, `name`, optional `description`. `ProjectAssignmentCreate`: `project_id`. `ProjectAssignmentStatusUpdate`: `in_progress`, `completed`, or `cancelled`; `assigned` to `in_progress`/`cancelled`, and `in_progress` to `completed`/`cancelled` are allowed. Completion timestamp and audit event are recorded.

## Certificates

| Method and path | Access | Operation |
| --- | --- | --- |
| `POST /api/v1/certificates` | Admin | Issue a certificate for an enrollment |
| `GET /api/v1/certificates` | Admin | Search/filter/paginate certificate report |
| `GET /api/v1/certificates/{certificate_id}` | Admin | Read immutable issuance and derived status |
| `GET /api/v1/certificates/{certificate_id}/events` | Admin | Read correction/replacement/revocation history |
| `POST /api/v1/certificates/{certificate_id}/replacement` | Admin | Issue a replacement and mark the original replaced atomically |
| `POST /api/v1/certificates/{certificate_id}/revocation` | Admin | Record a revocation reason |
| `POST /api/v1/certificates/{certificate_id}/corrections` | Admin | Record a traceable correction event without rewriting issuance |

`CertificateIssueCreate`: `enrollment_id`, `certificate_number`, `certificate_type`, optional timezone-aware `issued_at`, optional private `document_uri`. `CertificateReplacementCreate`: new `certificate_number`, optional issue time/document URI, and `reason`. `CertificateEventCreate`: `reason`. Certificate status is derived as `issued`, `replaced`, or `revoked`. There are no update or delete endpoints for issued certificates.

## SRS Coverage Not Yet Implemented

The current backend has no dashboard KPI endpoint, general report/export endpoint, or export audit workflow. Those are SRS requirements for a later sprint, not part of the current API surface. Exact date-range filters on batch/enrollment/payment lists are also not yet exposed. Production database role grants are not provisioned in this repository; production deployment must apply DBA-reviewed least-privilege roles before launch.
