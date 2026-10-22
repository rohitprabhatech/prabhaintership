# QA and Security Testing Report

**Date:** 2026-10-21  
**Status:** Partial; not a release approval or security certification.

The SRS and database design are drafts awaiting stakeholder approval. The explicit local MySQL request was followed. The SRS, database design, and `database/schema.sql` still specify PostgreSQL; reconcile those documents before treating them as an approved MySQL baseline.

## Evidence Summary

| Check | Result | Evidence |
| --- | --- | --- |
| Application-configured MySQL connection | Passed | `python -m app.cli verify-db` connected to `localhost:3306/internship_management` on MySQL 9.5.0. The command reported 42 existing Admin accounts; no password or URL was printed. |
| MySQL driver and ORM | Passed | Backend dependencies declare PyMySQL and SQLAlchemy; the application connected successfully using `mysql+pymysql`. |
| Alembic state and migration | Passed | Local database advanced from revision `0007` to `0008`; migration `0008` changes only the certificate-status view projection. |
| Schema objects and integrity metadata | Passed | All 16 expected application tables, `alembic_version`, and 3 MySQL views exist. SQLAlchemy inspection found 30 foreign keys, 61 indexes, 24 unique constraints, and 50 check constraints. |
| Backend unit/non-integration suite | Passed | From `backend`: `python -m pytest -q` -> 24 passed, 27 skipped, 1 Starlette deprecation warning. The 27 database tests skip without `TEST_DATABASE_URL`. |
| Backend MySQL integration suite | Passed | `python -m pytest -q` against isolated QA schema `internship_management_qa_a59c0e43` -> 51 passed, 2 warnings. The schema was migrated through `0008`; it contains synthetic test records. |
| Frontend Vitest suite | Passed | `npm test -- --no-cache --reporter=dot` -> 3 files and 20 tests passed. |
| Frontend production build | Passed | `npm run build` completed successfully with Vite 6.4.4. |
| Local startup smoke tests | Passed with port caveats | The launched backend returned 200 from `/api/v1/health/live` on port 18080, and a launched Vite process served `/login` with 200 on port 5174. Ports 8000 and 5173 already had listeners; neither was stopped or modified. |
| Secret-ignore rules | Passed | `backend/.env` exists, is not tracked, and is ignored by Git. `.env.example` contains placeholders only. Secret values were not printed or included in documentation. |
| Backend Ruff checks | Failed | `ruff check app tests migrations --statistics` reports 187 findings in the current worktree: 127 E501, 30 I001, 26 F401, 3 UP017, and 1 F541. They were not mass-fixed as unrelated style cleanup. |
| Security review | No high-confidence findings | Read-only source review found no high-confidence vulnerabilities. This is not a penetration test or production certification. |

## Requirements-to-Test Traceability

| SRS requirement group | Test evidence / intended test cases | Result |
| --- | --- | --- |
| FR-AUTH-01..06, AC-01.1..4: Admin authentication, protected routes, generic failures, throttling, expiry | `tests/test_auth_api.py`, `tests/test_students_auth_guard.py`, `tests/test_security.py` | Database-backed auth/security tests passed in the 51-test MySQL integration run. No server logout endpoint is exposed; sign-out disposes the client token. |
| FR-STU-01..04, AC-02.1..3: Student CRUD, search, filters, pagination, archive/history | `tests/test_student_schemas.py`, `tests/test_students_api.py` | Schema and MySQL API tests passed. |
| FR-PROG-01, FR-BATCH-01..03, FR-ENR-01..05, AC-03/04 | `tests/test_programs_batches_enrollments_api.py` | MySQL integration tests passed. |
| FR-FEE-01, FR-PAY-01..03, FR-BAL-01..05, AC-05.1..5: installments, amounts, idempotency, overpayment, concurrency, balances | `tests/test_finance_projects_certificates_api.py` | MySQL tests passed, including overpayment, idempotency, and concurrent payment coverage. |
| FR-PRJ-01..02, FR-CERT-01..04, FR-AUD-01..03, AC-06/07 | `tests/test_finance_projects_certificates_api.py` and `tests/test_auth_api.py` | MySQL project, certificate lifecycle, and audit tests passed after the certificate view and test-isolation defects were corrected. |
| FR-DASH-01..02, FR-SEARCH-01, FR-FILTER-01, FR-PAGE-01, FR-EXPORT-01..02, AC-08..10 | Frontend pages, backend router inspection | Student search/filter/pagination tests passed. Dashboard/report/export API requirements remain incomplete: no matching backend routes were found. |
| NFR-SEC-01..06: authorization, secret handling, input/error safety, dependency review | `tests/test_security.py`, `tests/test_production_settings.py`; source review | Application tests passed and source review found no high-confidence issue. No external dependency vulnerability scan, penetration test, or browser XSS/CSRF test was run. |
| NFR-OPS-01..04, AC-11: backups, restore, recovery | No test executed | Not run; no backup/restore procedure was exercised. |
| Responsive UI and accessibility | Frontend tests/browser inspection | Not run; no viewport, keyboard, or assistive-technology evidence. |
| Clean database migration | Alembic on isolated MySQL schema | Passed through revision `0008`; the existing local database was also advanced from `0007` to `0008`. No base-table records were changed by migration `0008`. |

## Failed, Blocked, and Not Run

- **Corrected during QA:** Successful-login audit assertions now scope to the test Admin; certificate reads now include `created_at`, and certificate pagination uses MySQL `LIMIT ... OFFSET` syntax. The full MySQL integration suite passed after these corrections.
- **Passed:** Backend non-integration tests (24); isolated MySQL integration tests (51); frontend Vitest tests (20); Vite production build; backend and frontend startup smoke checks.
- **Failed:** Ruff reports 187 lint findings; see Evidence Summary. No unrelated mass formatting was applied.
- **Not run:** Dependency vulnerability scan, browser XSS/CSRF and accessibility checks, backup/restore drill, performance testing, or production deployment validation.

## Data Safety Incident

An earlier QA attempt (before this verification session) loaded development settings before selecting its test database and wrote generated records to `internship_management`. The previously recorded incident count was 42 Admin rows, 76 audit logs, 38 students, 28 programs, 26 batches, 24 enrollments, 24 fee terms, 12 payments, and other test-like records. A read-only check in this session again found 42 Admin accounts. Treat these accounts/records as untrusted test data until the database owner reviews them.

No records or tables were deleted. Migration `0008` was applied to the local database; it replaces only `v_certificate_status` to expose the existing certificate `created_at` column and does not issue DML against base tables. Do not use or bootstrap any of the existing Admin accounts until the database owner reviews the data. Cleanup is intentionally not attempted; restore from a known backup or authorize narrowly scoped cleanup only after owner review.

This session created the isolated QA schema `internship_management_qa_a59c0e43` for MySQL integration tests. It contains synthetic test rows and was not dropped. Do not use it as application data; the database owner may remove this specifically identified QA schema after retaining any needed test evidence.

## Verified Defects and Remaining Risks

- Integration tests require a separate `TEST_DATABASE_URL` and matching `DB_NAME` before application modules are imported; tests were run only against an isolated QA schema in this session.
- The SRS and `database/schema.sql` specify PostgreSQL, while the requested local runtime and current Alembic revisions use MySQL. `database/schema.sql` must not be executed against MySQL; Alembic revisions are the current MySQL schema source.
- Dashboard, reports, and exports have frontend pages but no corresponding backend API routes in `backend/app/api/router.py`.
- The requested MySQL database already contained all 16 application tables at revision `0007`; the premise that its tables were missing did not match the observed local database.
- The local application uses the MySQL `root` principal as explicitly requested. This is unsuitable for deployment; use separate least-privilege runtime, migration, and Admin-provisioning accounts.
- Dependency vulnerability scanning, browser XSS/CSRF, privacy/logging review under production conditions, accessibility, backup/restore, and production gates remain unverified.
