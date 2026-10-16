# Agile Sprint Plan

## Prabha Technology Pvt. Ltd. Internship Management System

| Document field | Value |
| --- | --- |
| Version | 0.1 Draft for approval |
| Source baseline | `SRS.md` v0.1 |
| Scope | Admin-only MVP |
| Currency | INR by default |
| Status | Awaiting approval; no code authorized by this plan |

## 1. Planning Basis

This plan treats the SRS as the approved functional baseline, as directed in the request that initiated this plan. The SRS file itself still says "Draft" and "Pending review"; reconcile that document status and version before implementation starts. Any change to its confirmed scope requires an explicit decision and updated traceability.

The plan deliberately does not decide unresolved business or architecture policies. Those are Sprint 0 readiness gates or later story-level approval gates. Estimates are relative Fibonacci story points, not person-days or delivery commitments. Sprint length, team size, and velocity are not provided; for sequencing only, the delivery sprints are assumed to be two weeks, with a planning range of 18-21 points for a staffed cross-functional team. Reforecast after Sprint 2 using observed throughput.

### Priority policy

- **P0:** Security, data integrity, or core workflow; blocks MVP release if incomplete.
- **P1:** Required in the SRS baseline and included in this MVP plan; may follow P0 work but cannot be silently removed from release scope.
- **P2:** Deferred or optional capability, not a release requirement. Adding it requires explicit scope approval.

P1 does not mean "out of MVP." Every P0 and P1 story below is in the planned MVP unless the SRS is formally changed.

## 2. MVP Goal

Deliver a deployable internal application through which an authorized Admin can authenticate and administer students, programs, batches, enrollment history, enrollment-specific fees and installment payments, projects, certificates, operational KPIs, searchable/filterable/paginated lists, and authorized exports. Protect administrative APIs, maintain traceable financial/certificate/audit history, use versioned database migrations, and prove backup restoration and deployment readiness.

There will be no student login, student dashboard, public registration, public application experience, or public API.

## 3. Epics and Traceability

| Epic | Outcome | SRS trace |
| --- | --- | --- |
| EP-01 Design and data foundation | Approved logical model, data rules, migration and test strategy | Sections 5, 7, 10 |
| EP-02 Admin identity and security | Secure Admin sign-in and server-enforced authorization | FR-AUTH-01 through FR-AUTH-06, NFR-SEC |
| EP-03 Student and offering administration | Maintain student profiles, programs, and batches without losing history | FR-STU, FR-PROG, FR-BATCH |
| EP-04 Enrollment and financial records | Independent enrollment history, fees, installment ledger, correct balances | FR-ENR, FR-FEE, FR-PAY, FR-BAL, BR-01 through BR-09 |
| EP-05 Project, certificate, and audit history | Manage projects and certificate issuance with traceable events | FR-PRJ, FR-CERT, FR-AUD, FR-LIFE |
| EP-06 Admin operations and reporting | KPIs, search, filters, pagination, controlled exports | FR-DASH, FR-SEARCH, FR-FILTER, FR-PAGE, FR-EXPORT |
| EP-07 Release and operations | Automated quality gates, protected backup/restore, deployment | NFR-OPS, NFR-SEC, NFR-MAINT |

## 4. Readiness Gate: Sprint 0 (No Delivery Points)

Sprint 0 is a pre-implementation decision and setup gate, not a feature sprint. It should finish before database design is baselined. Unresolved answers may be explicitly deferred only when the affected feature can be safely excluded without violating the approved MVP.

| Gate ID | Decision/output required before affected work starts | Owner(s) |
| --- | --- | --- |
| G0-01 | Confirm SRS approval/version and the Admin account count, bootstrap/provisioning, recovery, MFA, and identity-provider choice | Product owner, security |
| G0-02 | Approve student, program, batch, enrollment, project, and certificate minimum fields, requiredness, and identifiers | Product owner, data architect |
| G0-03 | Approve enrollment statuses/transitions, duplicate and simultaneous enrollment rules, and archive behavior | Product owner |
| G0-04 | Approve payment statuses, which count toward balances, fee-change/correction/reversal/refund rules, rounding, and overpayment exception authority | Finance owner, product owner |
| G0-05 | Approve certificate eligibility, identifiers, replacement/revocation, and whether document storage/generation is in MVP | Product owner |
| G0-06 | Approve KPI formulas/date ranges, MVP reports, search/filter fields, page-size bounds, export format/columns, and all-results vs current-page semantics | Product owner, operations |
| G0-07 | Select hosting/deployment target, secrets management, TLS termination, database operations, backup ownership, retention, RPO, and RTO | Operations, security |
| G0-08 | Agree expected record/concurrency volumes, supported browsers, accessibility target, and whether the proposed P95 target is binding | Product owner, QA, operations |
| G0-09 | Confirm privacy/data-retention obligations and production/non-production data handling | Privacy owner, security |

**Gate exit:** Decisions are recorded in the SRS or linked ADRs; owners accept remaining assumptions; no financial, access-control, or data-retention policy is silently inferred. Technical choices that materially affect authentication, money, audit immutability, or deployment require stakeholder/security approval before implementation.

## 5. Sprint Sequence and Goals

### Sprint 1 - Database design and quality blueprint

**Goal:** Approve the conceptual/relational model and critical data invariants before feature implementation. Story: US-DB-01, **8 points**. Dependency: Sprint 0 decisions G0-02 through G0-05; financial and historical policies must be settled enough to model safely.

**Deliverables:** ERD, data dictionary, relationship/cardinality rules, constraints and indexes, lifecycle/deletion policy, money and balance invariants, audit-event model, migration strategy, API resource map, test strategy, and approved ADRs. No feature is considered implemented by producing design artifacts.

**Demo checklist:** Walk the student -> enrollment -> program/batch -> fee/payment -> project/certificate relationships; demonstrate how a repeat enrollment remains independent; show how overpayment and negative balances are prevented by the model; review audit and migration approach.

**Exit criteria:** Product, data, backend, QA, and security representatives approve the model; each SRS entity and business invariant maps to a design element and test; no unresolved critical ambiguity remains in enrollment/payment/certificate history.

### Sprint 2 - Platform foundation and Admin access

**Goal:** Establish the application foundation, versioned migration workflow, Admin sign-in, and server-side authorization. Stories: US-PLAT-01 (5), US-AUTH-01 (8), US-AUTHZ-01 (5), **18 points**. Dependency: approved Sprint 1 design and G0-01, G0-07.

**Demo checklist:** Start the application in the approved dev/test environment; apply the initial Alembic migration to a clean PostgreSQL database; show Admin sign-in and sign-out/session expiry behavior; show protected API denial without credentials and access with Admin credentials; demonstrate no registration or student routes.

**Exit criteria:** Clean environment setup is documented; migration applies reproducibly; authentication and authorization tests pass; secrets are externalized; no protected API relies only on frontend route hiding.

### Sprint 3 - Student, program, and batch administration

**Goal:** Deliver foundational administrative records and responsive CRUD workflows. Stories: US-STU-01 (8), US-PROG-01 (5), US-BATCH-01 (5), **18 points**. Dependency: Sprint 2 foundation/auth; approved fields and lifecycle rules.

**Demo checklist:** Create/update/search/archive a student; create/activate a program; create and list its batches; verify required-field, invalid-date, and invalid-reference errors; show archived student history remains available to authorized Admin.

**Exit criteria:** Versioned schema migrations, protected APIs, responsive forms/list views, validation, pagination-ready list contracts, and focused API/UI tests are complete; historical references remain intact.

### Sprint 4 - Enrollment and enrollment-specific finance

**Goal:** Deliver multiple independent enrollments per student and reliable INR fee/installment accounting. Stories: US-ENR-01 (8), US-FIN-01 (13), **21 points**. Dependency: Sprint 3; approved enrollment and payment policies from G0-03/G0-04.

**Demo checklist:** Create two enrollments for one student; assign distinct fees; add installments to only one enrollment; verify the other enrollment is unchanged; show the INR 10,000.00 fee / INR 4,000.00 eligible-payment example yields INR 6,000.00 pending; attempt overpayment and verify rejection; show payment actor/time and correction/reversal history per policy.

**Exit criteria:** Decimal-safe arithmetic and transaction behavior are covered by unit/API/integration tests; DB constraints and API validation enforce relationships and amounts; concurrent/duplicate payment attempts cannot create an overpayment or negative balance; migration and rollback/recovery approach is verified.

### Sprint 5 - Projects, certificates, and audit history

**Goal:** Complete internship progress/certificate workflows and cross-cutting traceability. Stories: US-PRJ-01 (5), US-CERT-01 (5), US-AUD-01 (8), **18 points**. Dependency: Sprint 4 enrollment; approved status, eligibility, and correction rules.

**Demo checklist:** Create/update a project under an enrollment; issue a certificate for the correct student/enrollment; attempt an invalid or duplicate certificate identifier where uniqueness applies; replace/revoke without deleting issuance history; review actor/timestamp audit trail for project, certificate, financial, and archive actions.

**Exit criteria:** All writes are Admin-protected; schema and API preserve relationships and trace history; correction/replacement paths preserve original events; audit tests verify actor/action/target/time and sensitive-data minimization.

### Sprint 6 - Search, dashboard, pagination, and export

**Goal:** Make administrative records usable for daily operations and reporting. Stories: US-OPS-01 (8), US-DASH-01 (5), US-EXP-01 (5), **18 points**. Dependency: core records and audit event model; approved G0-06 definitions.

**Demo checklist:** Combine approved search terms and filters; navigate pages while retaining filters and total count; reconcile dashboard values with matching detail lists; choose a date range; export filtered results and verify file columns, scope, and audit event; verify exports omit disallowed fields.

**Exit criteria:** Server-side pagination/filtering is correct; KPI formulas have reconciliation tests; export behavior is documented, Admin-only, bounded, and audited; responsive layouts work at agreed desktop/tablet/mobile viewports without clipped or overlapping controls.

### Sprint 7 - Release hardening, backup/restore, and deployment

**Goal:** Prove the integrated MVP can be deployed, operated, secured, and recovered. Stories: US-OPS-02 (5), US-REL-01 (8), US-REL-02 (5), **18 points**. Dependency: all P0/P1 stories; G0-07/G0-08; selected staging/production environment.

**Demo checklist:** Deploy to the approved staging target using environment-based secrets; run migrations and health checks; execute full backend/frontend/API authorization regression suites; produce a protected backup; restore it to an isolated environment and verify representative student/enrollment/payment/certificate records and balances; review logs for secret/PII leakage; present release checklist and rollback procedure.

**Exit criteria:** All MVP release gates pass; staging deployment is repeatable; backup and restore meet approved RPO/RTO; critical security and financial defects are closed; monitoring/logging, rollback, migration, and operator runbooks are accepted; production go-live is separately approved.

## 6. User Stories, Priorities, Points, Acceptance Criteria, and Tasks

Task prefixes: **DB** database/design/migration; **BE** backend/API; **FE** frontend; **QA** testing/quality. Tasks are independently trackable; task IDs are unique. Acceptance criteria are story-level completion gates. Where an acceptance rule depends on an open SRS policy, the corresponding Sprint 0 gate must be resolved first.

### US-DB-01 - Approve relational model and invariants

**Epic:** EP-01 | **Sprint:** 1 | **Priority:** P0 | **Points:** 8 | **Depends on:** G0-02 to G0-05.

**Acceptance criteria:** (1) Approved ERD/data dictionary covers all SRS entities and history links. (2) Payment has exactly one enrollment relationship; money precision, balance invariant, overpayment rule, and allowed payment statuses are documented. (3) Unique keys, required fields, lifecycle/archive behavior, transaction-sensitive rules, and audit retention are documented. (4) API resource map and test matrix trace every SRS Must requirement to a story and test.

- **DB-DB01:** Produce ERD, data dictionary, constraints/indexes, money and history model, and Alembic strategy.
- **BE-DB01:** Review transaction boundaries, API resources, authorization points, and migration compatibility.
- **FE-DB01:** Map approved user workflows to fields, forms, list/detail needs, and error states.
- **QA-DB01:** Build requirement-to-test traceability and negative/edge-case matrix for all critical invariants.

### US-PLAT-01 - Establish application and migration foundation

**Epic:** EP-02 | **Sprint:** 2 | **Priority:** P0 | **Points:** 5 | **Depends on:** US-DB-01.

**Acceptance criteria:** (1) A clean developer/test environment can start frontend, backend, and PostgreSQL using documented configuration. (2) Alembic upgrades a clean database to the initial schema reproducibly. (3) Health checks report dependency readiness without exposing secrets. (4) CI runs formatting/lint or equivalent, migration validation, and test commands.

- **DB-PL01:** Add initial Alembic baseline and verify clean-database upgrade.
- **BE-PL01:** Establish FastAPI configuration, SQLAlchemy session lifecycle, health/readiness endpoints, and structured safe errors.
- **FE-PL01:** Establish Vite/Tailwind app shell, routing boundary, responsive admin layout foundation, and environment-based API configuration.
- **QA-PL01:** Add CI smoke checks, test configuration, migration smoke test, and secret/configuration checks.

### US-AUTH-01 - Authenticate the authorized Admin

**Epic:** EP-02 | **Sprint:** 2 | **Priority:** P0 | **Points:** 8 | **Depends on:** US-DB-01, G0-01.

**Acceptance criteria:** (1) A provisioned Admin can sign in and sign out using the approved identity/session design. (2) Invalid credentials receive a generic failure response; repeated attempts follow approved throttling policy. (3) Credentials are adaptively hashed if locally managed; no public registration endpoint exists. (4) Session expiration and recovery behavior match the approved policy.

- **DB-AU01:** Add versioned Admin identity/session persistence only if selected auth design requires it; enforce uniqueness/state constraints.
- **BE-AU01:** Implement approved authentication, secure password verification if local, provisioning path, logout/expiry, and failure throttling.
- **FE-AU01:** Build responsive Admin sign-in/out screens and session-expired state; do not expose registration.
- **QA-AU01:** Test valid/invalid credentials, enumeration resistance, throttling, expiry, logout, provisioning, and secret-safe logging.

### US-AUTHZ-01 - Enforce Admin-only API and UI access

**Epic:** EP-02 | **Sprint:** 2 | **Priority:** P0 | **Points:** 5 | **Depends on:** US-AUTH-01.

**Acceptance criteria:** (1) Every protected API rejects missing, invalid, or expired identity. (2) An authenticated Admin can access only Admin operations; future/non-admin identities are denied by default. (3) Direct URL/API calls cannot bypass authorization. (4) No student login, dashboard, public application, or public registration route is shipped.

- **DB-AZ01:** Add only the role/identity constraints required by the approved single-role model.
- **BE-AZ01:** Apply centralized server-side authentication/authorization dependencies to every protected route; configure safe CORS/CSRF controls per approved session design.
- **FE-AZ01:** Guard admin routes for usability while treating server authorization as authoritative; add denied/session-expired states.
- **QA-AZ01:** Enumerate API routes and test 401/403 behavior, direct navigation, expired sessions, and absence of out-of-scope routes.

### US-STU-01 - Maintain student profiles and history

**Epic:** EP-03 | **Sprint:** 3 | **Priority:** P0 | **Points:** 8 | **Depends on:** US-PLAT-01, US-AUTHZ-01, US-DB-01.

**Acceptance criteria:** (1) Admin can create, view, edit, search, and archive profiles using approved fields. (2) Invalid required fields/formats are rejected without partial writes. (3) Archiving a referenced student preserves all enrollment and downstream history. (4) All profile APIs and screens are Admin-only.

- **DB-ST01:** Add student migration, approved field constraints, indexes, and archive/history rules.
- **BE-ST01:** Implement validated student CRUD/archive/search APIs and non-destructive lifecycle behavior.
- **FE-ST01:** Implement responsive student list/detail/form, validation feedback, empty/loading/error states.
- **QA-ST01:** Test field validation, duplicate rules, search, archive with dependent history, authorization, and UI flows.

### US-PROG-01 - Manage internship programs

**Epic:** EP-03 | **Sprint:** 3 | **Priority:** P0 | **Points:** 5 | **Depends on:** US-PLAT-01, US-AUTHZ-01, US-DB-01.

**Acceptance criteria:** (1) Admin can create/view/edit/search and activate/deactivate a program using approved fields. (2) Required fields and lifecycle transitions are enforced at API and database boundaries where applicable. (3) Program edits do not rewrite historical enrollment associations.

- **DB-PR01:** Add program migration, constraints, lifecycle fields, and indexes.
- **BE-PR01:** Implement validated program APIs and historical relationship behavior.
- **FE-PR01:** Implement responsive program list/detail/form and lifecycle controls.
- **QA-PR01:** Test CRUD, validation, lifecycle rules, historical associations, and protected access.

### US-BATCH-01 - Manage program batches

**Epic:** EP-03 | **Sprint:** 3 | **Priority:** P0 | **Points:** 5 | **Depends on:** US-PROG-01, US-DB-01.

**Acceptance criteria:** (1) Admin can create/view/edit/list batches associated with a valid program. (2) Required dates and lifecycle transitions follow approved rules. (3) Program/batch changes cannot silently move existing enrollment history.

- **DB-BA01:** Add batch migration, program foreign key, date/status constraints, and indexes.
- **BE-BA01:** Implement batch APIs with relationship/date validation and history-safe edits.
- **FE-BA01:** Implement responsive batch management views scoped/filterable by program.
- **QA-BA01:** Test invalid relationships/dates, program filters, status transitions, history preservation, and authorization.

### US-ENR-01 - Create distinct enrollment history

**Epic:** EP-04 | **Sprint:** 4 | **Priority:** P0 | **Points:** 8 | **Depends on:** US-STU-01, US-PROG-01, US-BATCH-01, G0-03.

**Acceptance criteria:** (1) One student can hold at least two distinct enrollment records. (2) Each enrollment references one student, one program, and the approved batch relationship. (3) Status/date/duplicate/overlap rules are enforced. (4) Changes to profile, program, or batch do not merge or silently rewrite historical enrollment facts.

- **DB-EN01:** Add enrollment migration, foreign keys, uniqueness/overlap constraints as approved, history-safe references.
- **BE-EN01:** Implement enrollment lifecycle APIs and validation; ensure transaction-safe creation.
- **FE-EN01:** Implement enrollment create/detail/list flows with student/program/batch selection and status history.
- **QA-EN01:** Test repeat and simultaneous enrollment cases per policy, invalid dates/references, lifecycle, history, and authorization.

### US-FIN-01 - Record enrollment fees and installment payments

**Epic:** EP-04 | **Sprint:** 4 | **Priority:** P0 | **Points:** 13 | **Depends on:** US-ENR-01, G0-04.

**Acceptance criteria:** (1) Fee and payment amounts use decimal-safe INR values with approved precision/rounding. (2) Each payment belongs to exactly one enrollment and includes required amount/date/actor/timestamp and approved method/reference/status. (3) Eligible payments for INR 10,000.00 fee totaling INR 4,000.00 yield INR 6,000.00 pending. (4) Overpayment is rejected by default, including concurrent submissions; balance never becomes negative. (5) Correction/reversal preserves original payment and audit linkage; partial failure cannot leave inconsistent balance state.

- **DB-FI01:** Add fee/payment-event migrations, exact decimal columns, constraints, indexes, and audit/correction relationships.
- **BE-FI01:** Implement transactional fee/payment APIs, enrollment-scoped balance calculation, approved overpayment policy, and idempotent/concurrency-safe handling.
- **FE-FI01:** Implement fee and installment forms, enrollment payment ledger, pending balance display, validation, and correction flow permitted by policy.
- **QA-FI01:** Test rounding, partial/full payment, overpayment, concurrency, status eligibility, reversal/correction, cross-enrollment isolation, and non-negative invariant.

### US-PRJ-01 - Track internship projects

**Epic:** EP-05 | **Sprint:** 5 | **Priority:** P1 | **Points:** 5 | **Depends on:** US-ENR-01, G0-05.

**Acceptance criteria:** (1) Admin can create/view/update project records attached to the correct enrollment. (2) Only approved project statuses and transitions are accepted. (3) Meaningful project changes record actor/time and preserve required history.

- **DB-PRJ01:** Add project migration, enrollment relationship, approved status constraints, and history fields.
- **BE-PRJ01:** Implement validated project APIs and auditable status changes.
- **FE-PRJ01:** Implement responsive project management and enrollment-linked project views.
- **QA-PRJ01:** Test relationship, invalid transitions, audit attribution, list behavior, and authorization.

### US-CERT-01 - Issue and trace certificates

**Epic:** EP-05 | **Sprint:** 5 | **Priority:** P1 | **Points:** 5 | **Depends on:** US-ENR-01, G0-05.

**Acceptance criteria:** (1) Admin can issue a certificate linked to the correct student and enrollment with approved metadata. (2) Eligibility and identifier uniqueness follow approved policy. (3) Replacement/cancel/revoke preserves the original issuance and records actor/time/reason. (4) Document generation or storage is included only if approved at G0-05.

- **DB-CE01:** Add certificate issuance/event migration, uniqueness constraints, and traceable lifecycle relations.
- **BE-CE01:** Implement eligibility and issuance/replacement/revocation APIs without destructive overwrite.
- **FE-CE01:** Implement certificate issue/history/status views and validation.
- **QA-CE01:** Test eligibility, uniqueness, issue/replacement/revocation history, actor/time, and access control.

### US-AUD-01 - Preserve an administrative audit trail

**Epic:** EP-05 | **Sprint:** 5 | **Priority:** P0 | **Points:** 8 | **Depends on:** US-AUTH-01, US-ENR-01, US-FIN-01; audit event contract approved in Sprint 1.

**Acceptance criteria:** (1) Security-sensitive actions and create/update/archive actions for financial/certificate records record actor, timestamp, action, target, and outcome. (2) Ordinary application routes cannot edit or delete audit events. (3) Payment corrections and certificate replacements link to original events. (4) Logs avoid credentials and unnecessary personal data; access is restricted.

- **DB-AU02:** Add audit event migration, indexes/retention metadata, and integrity protections selected in design.
- **BE-AU02:** Implement centralized audit emission for auth, records, finance, certificates, and exports; prevent application-level mutation.
- **FE-AU02:** Add authorized history views where required; avoid exposing internal/security-only audit data in general screens.
- **QA-AU02:** Test event completeness, actor attribution, immutable-by-application behavior, correction links, sensitive-data minimization, and access.

### US-OPS-01 - Search, filter, and paginate records

**Epic:** EP-06 | **Sprint:** 6 | **Priority:** P1 | **Points:** 8 | **Depends on:** US-STU-01 through US-CERT-01; G0-06/G0-08.

**Acceptance criteria:** (1) Approved search fields and filters can be combined. (2) Pagination is server-side, returns no more than the configured page size, shows total count, and preserves filters between pages. (3) Invalid filters cannot broaden access. (4) Query behavior meets the approved performance target at the agreed representative dataset size.

- **DB-OP01:** Add/adjust indexes and query plans for approved search/filter/sort dimensions.
- **BE-OP01:** Implement validated query parameters, scoped filtering, deterministic ordering, and bounded pagination.
- **FE-OP01:** Implement reusable responsive list controls, search/filter state, page navigation, and empty/error states.
- **QA-OP01:** Test combined filters, page boundaries, stable ordering, invalid inputs, authorization, representative-volume performance.

### US-DASH-01 - Review dashboard KPIs

**Epic:** EP-06 | **Sprint:** 6 | **Priority:** P1 | **Points:** 5 | **Depends on:** US-ENR-01, US-FIN-01, US-PRJ-01, US-CERT-01, G0-06.

**Acceptance criteria:** (1) Each approved KPI shows label, value, scope/date range, and empty state. (2) Every KPI reconciles to detail records under the same definitions and filters. (3) Financial KPIs use INR and decimal-safe aggregation. (4) Dashboard access and data are Admin-only.

- **DB-DA01:** Add only approved aggregation indexes/views if evidence shows they are needed; keep source records authoritative.
- **BE-DA01:** Implement KPI queries with explicit definitions/date boundaries and tests.
- **FE-DA01:** Implement responsive KPI dashboard and date-range controls using approved definitions.
- **QA-DA01:** Reconcile each KPI against seeded detail data, including empty data, date boundaries, and authorization.

### US-EXP-01 - Export authorized filtered records

**Epic:** EP-06 | **Sprint:** 6 | **Priority:** P1 | **Points:** 5 | **Depends on:** US-OPS-01, US-AUD-01, G0-06.

**Acceptance criteria:** (1) Export uses approved format, columns, size limit, filters, and all-results/current-page semantics. (2) Only Admin can export and export is audited. (3) Secrets and disallowed personal fields are excluded. (4) Output handles empty results and spreadsheet-formula injection according to security policy.

- **DB-EX01:** Confirm query/index support for bounded export and audit linkage; no separate data copy unless approved.
- **BE-EX01:** Implement authorized, bounded export generation, safe serialization, field allowlist, and audit event.
- **FE-EX01:** Implement export action with active-filter scope and clear success/failure states.
- **QA-EX01:** Test data scope, format, field allowlist, limits, injection safety, empty results, authorization, and audit.

### US-OPS-02 - Back up and restore production data

**Epic:** EP-07 | **Sprint:** 7 | **Priority:** P0 | **Points:** 5 | **Depends on:** G0-07, deployed database and approved operations ownership.

**Acceptance criteria:** (1) Backups run on the approved schedule and authorized operators can observe success/failure. (2) Backup access, encryption, retention, and transport follow approved policy. (3) Restore to an isolated target recovers representative linked records and produces correct enrollment balances. (4) A documented restore drill meets approved RPO/RTO.

- **DB-OP02:** Configure database backup/restore procedures, retention, access controls, and migration-aware recovery steps.
- **BE-OP02:** Add readiness/operational checks and safe recovery documentation for application compatibility.
- **FE-OP02:** Provide no backup controls to ordinary Admin users; document operator-only status visibility if a console is in scope.
- **QA-OP02:** Execute and record backup/restore drill; verify counts, links, audit history, balances, and RPO/RTO evidence.

### US-REL-01 - Deploy the integrated MVP

**Epic:** EP-07 | **Sprint:** 7 | **Priority:** P0 | **Points:** 8 | **Depends on:** all MVP stories, G0-07/G0-08.

**Acceptance criteria:** (1) Staging deployment is repeatable from documented steps or pipeline. (2) Secrets are injected from approved configuration/secret store and are not present in source or build artifacts. (3) TLS, health checks, migrations, logs, and rollback procedures operate in the selected environment. (4) Production release requires explicit go-live approval.

- **DB-RE01:** Provision/configure PostgreSQL, migration release procedure, restricted credentials, and restore compatibility.
- **BE-RE01:** Package/configure FastAPI service, production-safe settings, health checks, and deployment/rollback procedure.
- **FE-RE01:** Build and deploy frontend with environment-safe API origin, HTTPS, and production error handling.
- **QA-RE01:** Run deployment smoke, migration, auth, API, UI, security configuration, and rollback checks in staging.

### US-REL-02 - Complete MVP integration and release verification

**Epic:** EP-07 | **Sprint:** 7 | **Priority:** P0 | **Points:** 5 | **Depends on:** all P0/P1 stories.

**Acceptance criteria:** (1) End-to-end Admin scenarios pass from sign-in through student/program/batch/enrollment/payment/project/certificate, reporting, and export. (2) Critical API authorization and financial invariants pass automated regression tests. (3) Responsive UI is verified at approved viewports and supported browsers. (4) No unresolved release-blocking security, data-loss, or financial defects remain; residual risks are signed off.

- **DB-RE02:** Verify migration order, fresh-install and upgrade path, constraints, and backup/restore data integrity.
- **BE-RE02:** Run integrated API/security regression, validate error handling, and close critical backend defects.
- **FE-RE02:** Run integrated responsive workflow checks and resolve critical usability defects.
- **QA-RE02:** Execute regression/e2e suite, security checklist, defect triage, and release evidence report.

## 7. Story and Sprint Summary

| Sprint | Stories | Points | Required dependency/gate |
| --- | --- | ---: | --- |
| Sprint 1 | US-DB-01 | 8 | Sprint 0 decisions; approved data/security design |
| Sprint 2 | US-PLAT-01, US-AUTH-01, US-AUTHZ-01 | 18 | Sprint 1 design; Admin identity and hosting decisions |
| Sprint 3 | US-STU-01, US-PROG-01, US-BATCH-01 | 18 | Platform/auth; approved core fields |
| Sprint 4 | US-ENR-01, US-FIN-01 | 21 | Core records; enrollment and finance policies |
| Sprint 5 | US-PRJ-01, US-CERT-01, US-AUD-01 | 18 | Enrollment/finance; project/certificate/audit rules |
| Sprint 6 | US-OPS-01, US-DASH-01, US-EXP-01 | 18 | All domain records; approved KPI/export semantics |
| Sprint 7 | US-OPS-02, US-REL-01, US-REL-02 | 18 | Staging target; backup/RPO/RTO and release approvals |
| **Total** | **18 stories** | **119** | Reforecast after Sprint 2 |

### Dependency flow

`Sprint 0 decisions -> Sprint 1 database design approval -> Sprint 2 platform/auth -> Sprint 3 master records -> Sprint 4 enrollment/finance -> Sprint 5 project/certificate/audit -> Sprint 6 search/KPIs/exports -> Sprint 7 backup/deployment/release`

Cross-cutting QA, security review, accessibility/usability review, and migration validation run in every delivery sprint. Stories must not bypass prerequisite gates because of schedule pressure.

## 8. Definition of Ready (DoR)

A story may enter a sprint only when:

- It has an ID, epic, priority, estimate, owner, and trace to approved SRS requirement(s).
- User value and scope are clear; acceptance criteria are specific, testable, and agreed by Product and QA.
- Dependencies and external decisions are resolved or explicitly accepted as non-blocking with a named owner/date.
- Required data fields, relationships, lifecycle rules, and authorization behavior are known for the story.
- UI behavior has a reviewed workflow/wireframe or clear existing design convention; responsive/error/empty states are included.
- API contracts, migration impact, validation, audit needs, and backward-compatibility impact are understood.
- Test data and test approach are identified; no real personal/financial data is needed in non-production without approval.
- Story fits the sprint based on team capacity and has no hidden cross-team/environment dependency.

## 9. Definition of Done (DoD)

A story is done only when all applicable items are true:

- Acceptance criteria pass and are demonstrated; related SRS/story traceability is updated.
- Database changes use reviewed Alembic migrations; clean upgrade and required upgrade/restore checks pass; constraints protect critical invariants.
- Backend validation, authorization, safe error handling, and audit behavior are implemented server-side.
- Frontend behavior is responsive and includes loading, empty, success, and validation/error states; no public/student workflow is introduced.
- Unit, API, integration, and frontend tests appropriate to the risk pass; critical negative cases are covered.
- Security/privacy review finds no unresolved high/critical issue; no secrets or unnecessary personal data appear in logs or exports.
- Code/configuration is reviewed and meets project lint/type/build conventions; environment configuration is documented.
- Documentation, operational notes, and known limitations are updated; no unapproved requirement or data-model decision is introduced.

**MVP release DoD:** All P0 and P1 stories accepted; all release gates pass; migrations apply cleanly; auth and authorization suite passes; finance invariants and traceability tests pass; backup restore meets approved objectives; staging deployment and rollback are demonstrated; production go-live is explicitly approved.

## 10. Testing Strategy and Quality Gates

- **Database:** Migration smoke tests against clean PostgreSQL, constraints/relationships, indexes for agreed query paths, transaction/concurrency tests for payments, and backup/restore data checks.
- **Backend:** Pytest unit tests for domain rules; API tests for validation, auth/authorization, CRUD, filters, pagination, balances, audit, and exports; integration tests against PostgreSQL.
- **Frontend:** Component/interaction tests for forms, errors, protected routes, tables/filters/pagination, dashboard, payments, and exports; browser-level workflow coverage for critical Admin journeys.
- **Security:** Route inventory and negative authorization tests; authentication policy checks; input and export safety; dependency/configuration scan; verify no secrets/PII leakage in errors/logs.
- **Responsive and accessibility:** Verify agreed supported browsers and viewport set; keyboard-operable forms/tables and status communication not dependent on color alone.
- **Release:** Full regression on staging, migration-upgrade test, health checks, backup/restore drill, rollback rehearsal, and signed release evidence.

No test result is implied by this plan. Tests will be reported only after execution in the implementation phase.

## 11. Risks, Controls, and Contingencies

| Risk | Impact | Control/contingency |
| --- | --- | --- |
| SRS file remains marked draft although planning request calls it approved | Scope/version ambiguity during implementation | Product owner updates approval metadata and baseline before Sprint 1 exit |
| Finance policy unresolved | Incorrect pending balances, overpayment, or misleading history | G0-04 blocks finance schema/API; do not substitute assumptions for policy |
| Authentication approach or Admin bootstrap unresolved | Access-control gap or inaccessible system | G0-01 blocks auth implementation; security review of selected approach |
| Historical enrollment and deletion rules unresolved | Broken traceability or accidental data loss | Sprint 1 model approval; archive/correction behavior tested with dependent records |
| Data volume and user capacity unknown | Slow queries/exports or capacity issue | G0-08 sets workload and acceptance baseline; profile representative dataset |
| KPI/export definitions unclear | Inconsistent reporting or privacy leak | G0-06 approval and field allowlist tests before Sprint 6 completion |
| RPO/RTO/hosting not decided | Release cannot be safely deployed or recovered | G0-07 is a deployment blocker; production is not approved until restore evidence exists |
| Limited team capacity or unfamiliar stack | Sprint spillover and quality compression | Reforecast velocity after Sprint 2; split scope only through explicit product approval; do not remove security/finance tests |
| Migration or deployment changes fail in production | Downtime/data loss | Staging rehearsal, backward-compatible migration review, backups, rollback and restore drill |
| Audit data captures excess personal data | Privacy/compliance exposure | Minimize audit payloads and review log/export fields with security/privacy owners |

## 12. Deferred Features (P2 / Out of MVP)

These are not implied by the SRS and are explicitly deferred unless separately approved. They must not be added during MVP without a scope decision.

| Deferred feature | Reason/dependency |
| --- | --- |
| Student login, self-service dashboard, public registration, public application page | Explicitly out of scope; no student/public role |
| Online payment gateway, automated reconciliation, payment webhooks | Manual payment recording is the planning assumption; financial integration is not in SRS scope |
| Automated email/SMS/WhatsApp notifications | Not required by the SRS; would introduce external-service/privacy decisions |
| Automated certificate generation, signing, or delivery | Only manual issuance tracking is baseline unless G0-05 approves document generation |
| Multi-currency accounting | INR is the default; other currencies require approved policy and model change |
| Advanced analytics, forecasting, custom report builder, scheduled report delivery | Beyond the agreed operational KPI/report/export baseline |
| Bulk student import/export templates and spreadsheet synchronization | Not specified; requires field mapping, validation, and duplicate-resolution policy |
| Additional roles, fine-grained permissions, multi-tenant/customer support | The system has one Admin role and one company scope in the SRS |
| Mobile-native application or offline mode | Responsive web UI is the MVP target |
| Payroll, accounting/general ledger, LMS, or public website | Explicitly outside current business scope |

Security, authorization, audit, data privacy, backups, restore testing, and deployment are not deferred features; they are MVP release requirements.

## 13. Approval and Change Control

Before implementation begins, approve this plan and synchronize the SRS status/version. Record decisions for Sprint 0 gates in the SRS or approved ADRs. Any feature, priority, data-policy, or acceptance-criteria change must identify affected requirement/story/task IDs and assess financial integrity, history, security, test coverage, and schedule impact.

**Approval status:** Pending stakeholder approval. No code has been written as part of sprint planning.
