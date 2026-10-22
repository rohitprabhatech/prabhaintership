# QA Defect and Readiness Report

**Application:** Prabha Technology Pvt. Ltd. Internship Management System  
**Report type:** Source-inspection QA summary and manual-test preparation  
**Manual execution:** Not performed for this report. See [09-manual-test-cases.md](./09-manual-test-cases.md); all manual cases remain **Not Run**.  
**Release decision:** Not a production approval, penetration-test report, or acceptance sign-off.

## 1. Executive Summary

The current repository contains a working Admin-only management application with React/Vite pages, FastAPI APIs, SQLAlchemy models, MySQL migrations, and automated tests. Core workflows exist for programs, batches, students, enrollments, fee terms, payment records and adjustments, projects, and certificate lifecycle. An Admin Change password feature is also implemented.

Source inspection did not constitute browser or live manual verification. The following functional gaps require product-owner decisions before the system can be considered complete against broader business requirements:

1. General reports and exports are not implemented by the backend; a Reports page exists but is not backed by report/export API routes.
2. Fee-structure data exists in the database model/table, but there is no fee-structure management API or UI. The enrollment flow records the initial agreed fee directly.
3. Certificate issuance currently requires an existing enrollment but does not enforce project-completion or fee-clearance eligibility.
4. The Overview page composes its counters and fee totals from multiple existing APIs; there is no aggregate dashboard endpoint or global recent-payment endpoint.

No new runtime defect was reproduced during preparation of these documents. Each manually observable item below must remain a hypothesis or known limitation until it is confirmed in the intended environment.

## 2. Findings and Limitations

Severity and priority are preliminary impact assessments from implementation evidence, not user-accepted business requirements.

| ID | Severity / priority | Finding | Evidence and impact | Recommended disposition |
| --- | --- | --- | --- | --- |
| QA-GAP-01 | Medium / P2 | General reports and export workflows are not implemented. | The frontend has a Reports page, but the API router has no report/export routes. Users cannot rely on general reporting, CSV output, or export audit trail. | Agree required report definitions, filters, access, export formats, and audit needs; then plan a dedicated feature sprint. |
| QA-GAP-02 | Medium / P2 | Fee structures cannot be managed or selected in the UI. | `fee_structures` model/table exists, but no CRUD API/UI was found. Enrollment creation takes an agreed fee and reason directly; `fee_structure_id` may be null. | Decide whether fee structures are required in the first release. If so, design authorization, effective dating, and enrollment snapshot behavior before adding endpoints. |
| QA-GAP-03 | Medium / P2 | Certificate business eligibility is not enforced by the service. | Certificate issue flow verifies the referenced enrollment exists; it does not require completed project or cleared balance. An Admin can issue against an otherwise incomplete enrollment. | Stakeholder must define eligibility. Add service-level validation and tests only after business rules are approved. |
| QA-GAP-04 | Low / P3 | No global recent-payment feed is available on the Overview. | The Overview uses enrollment and fee APIs; there is no global recent-payment endpoint in the current API router. | Decide whether an operational payment feed is required; add a paginated, authorized API/UI if approved. |
| QA-GAP-05 | Medium / P2 | Dashboard summary is assembled by multiple browser requests. | `loadDashboard` fetches several paginated totals, all enrollment fee summaries, then detail lookups for recent enrollments. It is not a single summary API. Larger datasets may increase request count and latency; this is a scalability risk, not a measured performance failure. | Measure with representative data and define response-time/data-volume targets before optimizing. |
| QA-GAP-06 | High / P1 | Local application database contains test-generated/unreviewed records and multiple Admin rows. | Prior QA evidence recorded 42 Admin rows plus generated business/audit data in `internship_management`; see the data-safety note below. Rows were not cleaned up. | Database owner must review provenance and decide on backup restore or narrowly scoped cleanup. Do not use, bootstrap, deactivate, or delete accounts/rows before that review and explicit authorization. |
| QA-GAP-07 | High / P1 | Local runtime uses MySQL `root` principal. | Existing local setup/testing report says the application uses the `root` principal. This is unsuitable for deployment and violates least privilege if carried into a deployed environment. | Before deployment, provision separate least-privilege runtime, migration, and Admin-provisioning principals and verify grants. Do not change local credentials as part of this documentation task. |
| QA-GAP-08 | Medium / P2 | Draft database/SRS documentation conflicts with implemented database engine. | Earlier QA inspection found `SRS.md`, `docs/03-database-design.md`, and `database/schema.sql` describe PostgreSQL, while current backend/Alembic revisions use MySQL. `database/schema.sql` must not be run against MySQL. | Reconcile and obtain architecture approval; use Alembic as current MySQL schema source until the design docs are corrected. |
| QA-GAP-09 | Unrated / P2 | Browser layout, accessibility, CSRF/XSS, performance, and recovery behavior are not fully verified. | Existing test report records no responsive viewport/assistive-technology testing, dependency vulnerability scan, external penetration test, backup/restore drill, or performance testing. | Schedule these against an isolated environment with agreed acceptance criteria; do not infer pass from source review or unit tests. |
| QA-GAP-10 | Low / P3 | Admin sign-out is client-token disposal, not server-side logout. | No server logout route/session store was found; JWT validity is checked through Admin `is_active` and `auth_version`, and client sign-out discards the token. | Current behavior is consistent with stateless bearer JWTs. Confirm acceptable token lifetime/revocation policy; do not describe client sign-out as server-side session termination. |

## 3. Prior Data-Safety Event (Historical Evidence)

The existing [05-testing-report.md](./05-testing-report.md) records an earlier QA attempt that wrote generated test data to the configured `internship_management` database after development settings were loaded. At the time of that report, read-only inspection observed 42 Admin rows and reported test-like business and audit data. The report states that no rows/tables were deleted and that cleanup was intentionally not attempted.

The same historical report records an isolated MySQL test schema named `internship_management_qa_a59c0e43` containing synthetic rows and not dropped. Treat that named schema as separate from application data; do not drop it without database-owner review. These are historical statements from the prior report, not new DB queries performed while preparing documents 08–10.

**Safety requirement:** Before performing any write-oriented manual tests, confirm the selected environment/schema with the database owner and use a dedicated approved QA schema. Do not directly insert/delete/update rows in MySQL for manual test setup. Do not expose any Admin password/hash. Do not use existing Admin records as test accounts until reviewed.

## 4. Automated Test Evidence

The following results are reported in prior task context or the existing testing report; they were **not rerun while preparing these documentation files**. Results come from separate test runs and must not be added together as a single run.

| Evidence source | Previously reported result | Qualification |
| --- | --- | --- |
| `docs/05-testing-report.md` | Backend non-integration: 24 passed, 27 skipped; MySQL integration: 51 passed, 2 warnings; frontend: 20 passed; Vite build passed. | Historical QA run. Database-backed tests used isolated schema `internship_management_qa_a59c0e43`; that schema remains as noted above. |
| Later Change Password feature validation | Backend: 58 passed, 2 warnings against an isolated temporary MySQL schema; frontend: 23 passed; production build passed; Ruff and compilation reported passed. | Reported by the prior feature task; do not interpret as a fresh run for these docs. The temporary schema used for that run was reported removed. |
| Existing QA lint report | `ruff check app tests migrations --statistics` reported 187 findings (127 E501, 30 I001, 26 F401, 3 UP017, 1 F541). | Historical result, not rerun here. The prior report did not mass-fix unrelated style findings. |

For a new reproducible run, use the commands in [08-manual-testing-guide.md](./08-manual-testing-guide.md) and retain the output with the test run. Backend integration tests must use an isolated disposable test schema and the repository's test guard; never target `internship_management` or production.

## 5. Manual Test Execution Status

- No manual login, navigation, form submission, API call, MySQL query, mobile viewport check, or screen-reader check was performed while preparing this report.
- All records in [09-manual-test-cases.md](./09-manual-test-cases.md) are correctly left as `Not Run`.
- The synthetic sample workflow in [08-manual-testing-guide.md](./08-manual-testing-guide.md) is proposed input only. No sample records were created by this documentation task.
- Do not mark a test as passed based solely on source inspection or an automated test of a related function.

## 6. Recommended QA Exit Criteria

Before a release candidate is accepted:

1. Database owner reviews the application DB's existing test-generated records and the retained QA schema, chooses a documented recovery/cleanup plan, and validates an approved isolated QA target.
2. Product owner approves the required fee-structure workflow, certificate eligibility rules, and report/export scope or explicitly defers them.
3. MySQL test suite passes on an isolated schema; frontend tests and production build pass on the candidate commit.
4. Manual cases for authentication, password change, core enrollment/finance workflows, project/certificate history, and authorization are executed and evidenced using synthetic records.
5. Responsive layout, keyboard/accessibility, secure logging/secret handling, rate limiting, dependency scan, backup/restore, and performance acceptance checks are completed or explicitly accepted as deployment risks.
6. Runtime and migration DB grants are least privilege; DB/SRS documentation reflects the approved architecture; no production secrets are tracked.
7. Deployment and rollback are reviewed separately. This report provides no authorization to deploy or modify production.

## 7. Scope and Limitations

This report is based on source and repository documentation review plus prior test evidence stated above. It is not a new execution report, penetration test, privacy assessment, database backup/restore verification, or production readiness sign-off. All issues and risk ratings should be reviewed with the product owner, database owner, and security approver.
