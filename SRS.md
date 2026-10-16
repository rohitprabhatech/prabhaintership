# Software Requirements Specification

## Prabha Technology Pvt. Ltd. Internship Management System

| Document field | Value |
| --- | --- |
| Version | 0.1 Draft for review |
| Status | Awaiting stakeholder approval |
| Product type | Internal administrative web application |
| Default currency | INR (Indian Rupee) |

## 1. Purpose and Intended Audience

This Software Requirements Specification (SRS) defines the initial requirements for an internal system used by Prabha Technology Pvt. Ltd. to administer internship programs and their related student, batch, enrollment, fee, payment, project, and certificate records. It is intended for business stakeholders, product/project management, architecture, development, QA, security, and operations.

This is a requirements document, not a database schema, implementation plan, or authorization to begin implementation. Items identified as assumptions or open questions require review before the affected design decisions are finalized.

## 2. Project Objectives and Success Measures

### 2.1 Objectives

- Centralize administrative internship records and preserve their history.
- Give authorized Admin users a secure, efficient way to manage the full internship lifecycle.
- Associate every fee and payment with the correct enrollment and present an accurate, non-negative pending balance.
- Track project progress and certificate issuance with traceable changes.
- Provide searchable, filterable, paginated records, operational KPIs, and controlled data exports.
- Reduce reliance on disconnected spreadsheets and make financial and operational records easier to reconcile.

### 2.2 Proposed success measures

These are proposed evaluation measures; target values and reporting periods need stakeholder approval.

- All managed enrollments can be traced to one student and one internship program; a batch is associated when applicable.
- Every recorded payment is associated with exactly one enrollment, and the system can calculate that enrollment's pending balance from its fee and eligible payments.
- No displayed pending balance is below INR 0.00.
- Every certificate issuance and payment change is traceable to an actor and timestamp.
- Admin can find a record using approved search and filter fields and export the matching result set.

## 3. Scope

### 3.1 In scope

- Admin-only authentication and protected administrative operations.
- Student profiles and retained historical records.
- Internship program and batch management.
- Multiple enrollments for a student over time, with enrollment-specific fees and history.
- Fee schedules, installment payments, payment history, and pending-balance calculation.
- Project tracking and certificate issuance/status tracking.
- Dashboard KPIs, search, filtering, pagination, and data exports.
- Input validation, auditability, security, privacy controls, backups, and automated testing.

### 3.2 Explicitly out of scope

- Student accounts, student login, student dashboard, or student self-service.
- Public website, public registration, public application page, or public-facing APIs.
- Non-admin business roles, unless separately approved through a change to this SRS.
- Payroll, general ledger/accounting, payment-gateway processing, messaging campaigns, and learning-management features. These are not implied by payment recording or internship tracking.

## 4. User Classes and Access

### 4.1 Admin

The sole in-application user class. An authenticated Admin can perform the approved management, reporting, and export functions. Access must be denied by default to unauthenticated users and to any principal that is not an authorized Admin.

The phrase "one authorized Admin role" is interpreted as one role type, not necessarily one user account. Whether multiple Admin accounts are permitted is an open question. No student or public user class exists in the current scope.

## 5. Product and Technology Context

The requested technology baseline is React.js with Vite, JavaScript initially, and Tailwind CSS for the frontend; Python with FastAPI, PostgreSQL, SQLAlchemy 2.x, Alembic, and Pydantic for the backend; and Pytest plus appropriate frontend tests for verification. Secrets must be supplied through environment-based configuration or an approved secret store, not committed to source control.

The system is an internal web application. Hosting environment, identity provider, deployment topology, integrations, and operational service levels have not yet been selected.

## 6. Functional Requirements

Priority terms: **Must** is required for the initial release; **Should** is desirable and should be included unless explicitly deferred; **Open** requires a stakeholder decision.

### 6.1 Authentication and authorization

- **FR-AUTH-01 (Must):** The application shall require authentication before exposing administrative data or operations.
- **FR-AUTH-02 (Must):** The authorization model shall contain only the Admin role for the initial release. Protected API operations shall enforce authorization on the server, not only in the UI.
- **FR-AUTH-03 (Must):** There shall be no public account registration, student login, or student-facing dashboard.
- **FR-AUTH-04 (Must):** Passwords, if locally managed, shall be stored using a current adaptive password-hashing algorithm; plaintext and reversibly encrypted passwords are prohibited.
- **FR-AUTH-05 (Must):** Authentication failures and repeated login attempts shall be handled to reduce credential guessing risk. Exact rate limits and lockout behavior require security review.
- **FR-AUTH-06 (Open):** Admin provisioning, account recovery, MFA, session/token strategy, and session expiration shall be defined before implementation.

### 6.2 Student profiles

- **FR-STU-01 (Must):** Admin shall be able to create, view, update, search, filter, and archive student profiles.
- **FR-STU-02 (Must):** A profile shall support an agreed minimum set of identity and contact fields. Exact fields, requiredness, uniqueness rules, and sensitive-data classification are open questions.
- **FR-STU-03 (Must):** A student may have multiple enrollments over time. Student profile changes shall not rewrite or erase enrollment, payment, project, or certificate history.
- **FR-STU-04 (Must):** A student referenced by historical records shall not be hard-deleted through normal administrative workflows. Archival or another approved retention action shall preserve referential traceability.

### 6.3 Internship programs and batches

- **FR-PROG-01 (Must):** Admin shall be able to create, view, update, activate/deactivate, and search internship programs.
- **FR-PROG-02 (Must):** Program records shall include an agreed name, description, and lifecycle state; any additional fields such as duration or default fee are subject to stakeholder confirmation.
- **FR-BATCH-01 (Must):** Admin shall be able to create and manage batches associated with an internship program.
- **FR-BATCH-02 (Must):** Batch records shall support an agreed name or identifier, schedule/date range, and lifecycle state. Required fields and allowed transitions are open questions.
- **FR-BATCH-03 (Must):** Program or batch changes shall not silently alter the historical program/batch association of existing enrollments.

### 6.4 Enrollments and history

- **FR-ENR-01 (Must):** Admin shall be able to create and manage an enrollment connecting one student to one internship program and, where applicable, one batch.
- **FR-ENR-02 (Must):** A student may have multiple enrollments over time. Each enrollment shall have its own identifier, dates, lifecycle status, fee terms, payment history, project records, and certificate records as applicable.
- **FR-ENR-03 (Must):** The system shall retain enrollment history and shall not merge separate enrollments merely because the student or program is the same.
- **FR-ENR-04 (Must):** The system shall validate required relationships and dates before saving an enrollment. Duplicate or overlapping enrollment policy is not yet defined.
- **FR-ENR-05 (Open):** Whether simultaneous enrollments are permitted, and the allowed enrollment status transitions, require approval.

### 6.5 Fees, installment payments, and balances

- **FR-FEE-01 (Must):** Admin shall be able to record the agreed fee amount for a specific enrollment, in INR by default. Money values shall use decimal-safe storage and arithmetic, never binary floating-point calculations.
- **FR-PAY-01 (Must):** Admin shall be able to record installment payments against exactly one enrollment. A payment shall not be attached only to a student or program when the enrollment is known.
- **FR-PAY-02 (Must):** Each payment record shall retain an amount, transaction/payment date, recording actor and timestamp, and an agreed payment method/reference/status where applicable.
- **FR-PAY-03 (Must):** Payment history shall be traceable. Corrections, reversals, or status changes shall not silently overwrite the original financial event; the approved correction model remains to be decided.
- **FR-BAL-01 (Must):** The pending balance for an enrollment shall be calculated from that enrollment's fee and eligible payments under an approved payment-status policy.
- **FR-BAL-02 (Must):** A pending balance shall never be displayed or persisted as a negative value.
- **FR-BAL-03 (Must):** The system shall prevent an overpayment by default. It shall reject a payment that would make eligible payments exceed the enrollment fee unless an explicitly approved policy and permission permit that case.
- **FR-BAL-04 (Must):** Balance updates shall remain correct when payments are added, corrected, reversed, or when enrollment fee terms change, according to the approved correction policy.
- **FR-BAL-05 (Open):** Refunds, discounts, waivers, fee revisions, credit balances, rounding rules, and whether overpayments can ever be approved require business rules before implementation.

### 6.6 Projects and certificates

- **FR-PRJ-01 (Must):** Admin shall be able to create and track project records associated with the correct enrollment. Project fields, number of projects permitted per enrollment, and status workflow are open questions.
- **FR-PRJ-02 (Must):** Project changes shall retain enough history to identify meaningful status or ownership changes, subject to the approved audit policy.
- **FR-CERT-01 (Must):** Admin shall be able to record certificate issuance and its association with the correct student and enrollment.
- **FR-CERT-02 (Must):** Certificate issuance history shall be traceable, including issuance identifier/reference, issue date, recording actor, and timestamp, as applicable.
- **FR-CERT-03 (Must):** Corrections, replacement, cancellation, or revocation shall preserve the original issuance event and its history rather than erase it.
- **FR-CERT-04 (Open):** Eligibility rules, certificate number uniqueness, generated document storage, replacement, and revocation workflow require definition.

### 6.7 Dashboard, search, filters, pagination, and exports

- **FR-DASH-01 (Must):** The Admin dashboard shall present agreed operational and financial KPIs. Proposed KPIs are active students, active programs, current batches, enrollments by status, collections for a selected period, outstanding balances, projects by status, and certificates issued for a selected period. KPI definitions and default date ranges require approval.
- **FR-DASH-02 (Must):** KPI values shall be derived from persisted records and reconcile with the corresponding filtered detail records under the approved definitions.
- **FR-SEARCH-01 (Must):** Admin shall be able to search relevant records using approved fields, including student identity fields and program, batch, or enrollment identifiers where applicable.
- **FR-FILTER-01 (Must):** Admin shall be able to filter lists by relevant status, program, batch, dates, and payment/balance state where applicable. Exact filters by screen require approval.
- **FR-PAGE-01 (Must):** List views shall support server-side pagination with a visible current page and total/result count. The default and maximum page sizes require approval.
- **FR-EXPORT-01 (Must):** Admin shall be able to export authorized records, respecting selected filters and documented export semantics. File formats, maximum export size, and whether exports include all matching pages or only the current page are open questions.
- **FR-EXPORT-02 (Must):** Exports shall exclude secrets and fields not approved for operational use; export actions shall be auditable.

### 6.8 Audit and record lifecycle

- **FR-AUD-01 (Must):** The system shall record actor, timestamp, action, target record, and outcome for security-sensitive actions and create/update/archive operations on financial and certificate records.
- **FR-AUD-02 (Must):** Audit events shall make payment and certificate histories traceable and shall not be editable through ordinary application workflows.
- **FR-AUD-03 (Must):** Audit records shall avoid unnecessarily duplicating sensitive personal data. Retention, access, and tamper-resistance controls require policy approval.
- **FR-LIFE-01 (Must):** Records connected to financial or historical records shall be archived or corrected using a traceable process rather than deleted in a way that breaks history.

## 7. Business Rules and Validation

- **BR-01:** INR is the default currency. Other currencies are not in scope unless approved.
- **BR-02:** Each payment belongs to exactly one enrollment; it must not be ambiguously allocated across a student's enrollments.
- **BR-03:** The pending balance cannot be negative.
- **BR-04:** Overpayment is prevented unless a separately approved business policy permits it and records the approval.
- **BR-05:** Payment and certificate history must remain traceable after correction, reversal, replacement, or revocation.
- **BR-06:** Financial calculations use decimal-compatible values and approved precision/rounding rules.
- **BR-07:** Required fields, formats, ranges, relationships, and lifecycle transitions shall be validated both at the API boundary and through database constraints where applicable.
- **BR-08:** Invalid requests shall return a clear validation error and shall not partially update related records.
- **BR-09:** Date ordering, allowed statuses, uniqueness, and deletion/archive behavior must be defined for each entity before implementation.

## 8. External Interface Requirements

- **UI:** Responsive internal administrative web UI for desktop and tablet use; mobile behavior should remain usable. Supported browser versions and accessibility target are open questions.
- **API:** Protected FastAPI endpoints for administrative UI operations. API validation and authorization must be enforced server-side.
- **Database:** PostgreSQL is the system of record. Schema changes must be managed through versioned Alembic migrations.
- **Exports:** Admin-initiated downloads only; format and size policy are open.
- **External services:** No payment gateway, identity provider, email, SMS, or certificate-generation integration is assumed in this release.

## 9. Non-Functional Requirements

### 9.1 Security

- **NFR-SEC-01:** All non-public application and API operations shall require authenticated Admin authorization.
- **NFR-SEC-02:** Passwords shall be adaptively hashed if local credentials are used; secrets shall not be embedded in source code or committed configuration.
- **NFR-SEC-03:** Production traffic shall use TLS. Session/token storage, CSRF defenses, cookie settings, and token lifetimes shall follow the selected authentication design.
- **NFR-SEC-04:** The application shall validate and safely handle untrusted input, apply least privilege to database/service credentials, and avoid exposing stack traces or secrets in client-visible errors.
- **NFR-SEC-05:** Security events, failed authentication, exports, and sensitive record changes shall be logged at an approved level without logging credentials or unnecessary personal data.
- **NFR-SEC-06:** Dependencies and deployment configuration shall be reviewed for known vulnerabilities before release; security testing scope and cadence require approval.

### 9.2 Privacy and data handling

- **NFR-PRV-01:** Collect and expose only student personal data needed for approved internship administration.
- **NFR-PRV-02:** Student data, payment records, certificates, exports, and backups shall be accessible only to authorized Admins and approved operational personnel.
- **NFR-PRV-03:** Retention, deletion, correction, data-subject request handling, and applicable legal obligations shall be documented before production use.
- **NFR-PRV-04:** Non-production test data shall not contain real student personal or financial data unless explicitly approved and protected.

### 9.3 Reliability, backup, and recovery

- **NFR-OPS-01:** Production data shall be backed up on an approved schedule, with backup access restricted and backups protected in transit and at rest.
- **NFR-OPS-02:** Backup restoration shall be periodically tested and documented.
- **NFR-OPS-03:** Recovery Point Objective (RPO), Recovery Time Objective (RTO), backup retention, and disaster recovery ownership are open questions. No operational target is confirmed by this SRS.
- **NFR-OPS-04:** Application and database errors shall be logged with correlation information sufficient for troubleshooting without leaking secrets or unnecessary personal data.

### 9.4 Performance, usability, and maintainability

- **NFR-PERF-01 (Proposed):** Common list, detail, and dashboard requests should complete within 2 seconds at the 95th percentile under an agreed representative load. Workload and target need approval.
- **NFR-PERF-02 (Proposed):** Search, filters, and pagination should remain responsive at an agreed initial data volume. Expected student, enrollment, and payment counts are open questions.
- **NFR-USE-01:** Administrative workflows shall provide clear success, empty, loading, and validation-error states and shall not rely on color alone to communicate status.
- **NFR-MAINT-01:** Backend modules, frontend modules, migrations, configuration, and tests shall be organized so that the system can be maintained without coupling unrelated business domains.
- **NFR-MAINT-02:** Automated backend and frontend tests shall cover critical business rules; CI gates and minimum coverage targets require agreement.

## 10. Logical Information Requirements

The following are conceptual records, not a physical schema proposal:

- **Student:** identity/contact profile and lifecycle state.
- **Internship program:** program definition and lifecycle state.
- **Batch:** cohort/schedule associated with a program.
- **Enrollment:** student, program, optional batch, dates, status, and enrollment-specific terms.
- **Fee/payment history:** fee terms and payment events associated with an enrollment.
- **Project:** progress record associated with an enrollment.
- **Certificate issuance:** certificate event associated with a student and enrollment, including traceable lifecycle history.
- **Admin identity and audit event:** actor identity and traceable administrative/security action.

The database design phase shall define identifiers, cardinalities, uniqueness, constraints, indexes, deletion behavior, transaction boundaries, and migration strategy after the open business rules are resolved.

## 11. User Stories and Acceptance Criteria

### US-01: Secure Admin access

As an authorized Admin, I want to authenticate so that only approved staff can use the system.

- **AC-01.1:** An unauthenticated request to each protected API operation is rejected and does not return protected data.
- **AC-01.2:** An authenticated Admin can access only the operations allowed to the Admin role.
- **AC-01.3:** No public registration or student-login route is available.
- **AC-01.4:** Failed login attempts do not reveal whether a particular credential/account exists; rate-limit behavior follows the approved security policy.

### US-02: Maintain student records

As an Admin, I want to maintain student profiles so that internship records use consistent student information.

- **AC-02.1:** Admin can create, view, update, search, filter, and archive a student profile.
- **AC-02.2:** A profile with invalid or missing required fields is rejected with field-level validation feedback and is not partially saved.
- **AC-02.3:** Archiving a student with history preserves the linked enrollments, payments, projects, and certificates.

### US-03: Manage programs and batches

As an Admin, I want to manage programs and batches so that enrollments reference valid offerings and cohorts.

- **AC-03.1:** Admin can create and update a program and its batches, and can list them by lifecycle state.
- **AC-03.2:** A batch cannot be saved without its required program association and valid required dates.
- **AC-03.3:** Editing a program or batch does not silently rewrite historical enrollment associations.

### US-04: Preserve enrollment history

As an Admin, I want each student enrollment to be recorded independently so that repeat participation remains distinguishable.

- **AC-04.1:** One student can have at least two distinct enrollments, each with its own identifier and history.
- **AC-04.2:** Each enrollment references exactly one student and one program, plus no more than one batch where the model requires a batch.
- **AC-04.3:** Enrollment date and status validation follows the approved transition and overlap rules.

### US-05: Record installments and see balances

As an Admin, I want to record payments against an enrollment and see the remaining amount due.

- **AC-05.1:** Every payment is linked to exactly one enrollment and cannot be assigned to another enrollment implicitly.
- **AC-05.2:** Given a fee of INR 10,000.00 and eligible posted installments totaling INR 4,000.00, the displayed pending balance is INR 6,000.00.
- **AC-05.3:** A payment that would make eligible payments exceed the enrollment fee is rejected unless the approved overpayment exception applies.
- **AC-05.4:** No supported fee/payment adjustment produces a pending balance below INR 0.00.
- **AC-05.5:** Payment correction or reversal retains the original event and an auditable link to the correction.

### US-06: Track projects

As an Admin, I want to track project progress by enrollment so that internship work can be monitored.

- **AC-06.1:** Each project record is linked to the correct enrollment.
- **AC-06.2:** Only approved project statuses and valid transitions can be saved.
- **AC-06.3:** A project status change records its actor and timestamp according to the audit policy.

### US-07: Issue and trace certificates

As an Admin, I want to record certificate issuance so that the system provides a reliable issuance history.

- **AC-07.1:** Issuance is linked to the correct student and enrollment and captures required issuance metadata.
- **AC-07.2:** Duplicate certificate identifiers are rejected where uniqueness is required by the approved policy.
- **AC-07.3:** A replacement, cancellation, or revocation does not erase the prior issuance event; the actor, time, and reason are retained according to policy.

### US-08: Review dashboard KPIs

As an Admin, I want a dashboard of operational and financial KPIs so that I can monitor internship activity.

- **AC-08.1:** Each approved KPI displays a label, value, and applicable date range or scope.
- **AC-08.2:** KPI values reconcile with a query of the underlying records using the same definition, filters, and date range.
- **AC-08.3:** Empty datasets display a valid zero/empty state rather than an error or misleading value.

### US-09: Find and page through records

As an Admin, I want to search, filter, and paginate records so that I can locate the right information efficiently.

- **AC-09.1:** Approved search terms and filters can be combined and return only matching records.
- **AC-09.2:** Page navigation returns no more than the configured page size, preserves active filters, and reports the correct result count.
- **AC-09.3:** Invalid filter values are rejected or safely ignored according to documented API behavior; they do not broaden access or expose unauthorized data.

### US-10: Export records

As an Admin, I want to export an approved result set so that I can perform authorized operational review.

- **AC-10.1:** An export reflects the documented filter and pagination semantics and contains only approved columns.
- **AC-10.2:** Export access is Admin-only and each export is recorded in the audit log.
- **AC-10.3:** Export output does not include credentials, secrets, or fields excluded by the approved privacy policy.

### US-11: Recover from data loss

As an operations owner, I want protected backups and a tested restore procedure so that the service can recover from data loss.

- **AC-11.1:** A backup completes on the approved schedule and its success/failure is observable by authorized operators.
- **AC-11.2:** A restore test demonstrates recovery within approved RPO/RTO targets and is documented.
- **AC-11.3:** Backup access and retention follow the approved security and privacy policies.

## 12. Confirmed Requirements vs. Assumptions

### 12.1 Confirmed by the request

- The product is an internal Internship Management System for Prabha Technology Pvt. Ltd.
- Admin is the only application role; there are no student or public-facing application experiences.
- Admin manages students, internships/programs, batches, enrollments, fees, payments, projects, and certificates.
- Student profiles and historical records must be maintained; students may have multiple enrollments over time.
- Payments must belong to the correct enrollment; pending balances cannot be negative.
- Overpayments are prevented unless an approved policy allows them.
- Payment history and certificate issuance must remain traceable.
- Search, filters, pagination, reports, dashboard KPIs, and exports are required capabilities.
- INR is the default currency.
- Requested technology baseline and security, validation, database, migration, and testing expectations are stated in Section 5 and this SRS.

### 12.2 Assumptions requiring confirmation

- "Admin-only" defines a single role type; the number of Admin accounts is not constrained yet.
- Student and enrollment records should be archived rather than hard-deleted when history exists.
- Payments are manually recorded in the initial release; no payment gateway is implied.
- Dashboard KPI suggestions in FR-DASH-01 are candidates, not an approved final list.
- CSV is a possible initial export format, but no format is confirmed.
- Proposed performance target in NFR-PERF-01 is a discussion baseline, not an approved service level.
- No external identity provider, email/SMS provider, or certificate-generation integration is assumed.
- The application is for use by authorized company staff; deployment location and hosting controls remain undecided.

## 13. Risks and Mitigations

| Risk | Potential impact | Proposed mitigation |
| --- | --- | --- |
| Payment, refund, discount, or correction rules remain ambiguous | Incorrect balances or untraceable financial adjustments | Approve a written financial policy and acceptance examples before database design |
| Enrollment overlap and status rules are undefined | Duplicate or invalid enrollment history | Define allowed states, transitions, and concurrent-enrollment policy |
| Admin provisioning and account recovery are undefined | Unauthorized access or lockout from the system | Decide account ownership, bootstrap, recovery, MFA, and session policy before implementation |
| Personal-data fields and retention rules are unknown | Privacy exposure or improper retention | Minimize fields, classify data, and obtain privacy/legal review before production |
| KPI and export semantics are unspecified | Conflicting reports or accidental disclosure | Approve KPI formulas, date ranges, export columns, and pagination behavior |
| Backup/recovery objectives are unknown | Unacceptable data loss or recovery delay | Set RPO/RTO, retention, ownership, and restore-test cadence before deployment |
| Expected data volume and usage are unknown | Slow search, reporting, or exports | Establish workload estimates and performance acceptance targets during planning |

## 14. Essential Open Questions

These decisions affect requirements, data integrity, or security and should be answered before the relevant design work begins.

1. **Admin identity:** Is one Admin account required, or may there be multiple Admin accounts? Who provisions the first account, and is MFA required? Should authentication use a company identity provider or local credentials?
2. **Financial policy:** Are refunds, discounts, waivers, fee changes, payment reversals, or credit balances allowed? Who can approve an overpayment exception, and how is it recorded? Which payment statuses count toward pending-balance calculation?
3. **Enrollment policy:** Can a student have simultaneous enrollments? Which enrollment statuses and transitions are required? Are there duplicate enrollment constraints?
4. **Required data:** Which student profile fields are required, which are sensitive, and which identifiers must be unique? What are the required program and batch fields?
5. **Projects and certificates:** What project statuses and cardinality are needed? What makes an enrollment eligible for a certificate? Are certificate files generated/stored, and how are replacement and revocation handled?
6. **Dashboard and reporting:** Which KPIs and reports are mandatory for the first release? What date ranges, grouping, filters, and definitions should each use?
7. **Search, exports, and data volume:** Which fields need search/filter support? Which export formats are required, and should exports include all filtered results or only the visible page? What record volumes and concurrent Admin usage are expected?
8. **Privacy and retention:** What retention and deletion/correction policies apply to student, payment, certificate, audit, and backup data? Are there legal or organizational privacy requirements to meet?
9. **Operations:** What hosting environment is expected? What availability, RPO, RTO, backup retention, and restore-test targets should the service meet?
10. **Acceptance targets:** Are the proposed two-second P95 common-request target and any initial workload assumptions acceptable, or should different measurable performance targets be set?

## 15. Approval and Change Control

This SRS is a draft baseline. Stakeholders should approve the confirmed scope, resolve or explicitly defer open questions, and identify any changes before sprint planning. Requirements changes after approval should be recorded with their rationale, affected requirement/story IDs, priority, and impact on schedule, data, security, and tests.

**Approval status:** Pending review. No implementation work is authorized by this document alone.