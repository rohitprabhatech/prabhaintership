# Deployment Checklist

**Status:** Not approved for production deployment. The local database contains test-generated records (42 Admin accounts were observed) and requires owner review; production deployment was not attempted. Local migration `0008` was applied, but SRS/database-design documents still specify PostgreSQL.

## Secrets and Configuration

- [ ] Store database/JWT secrets in an approved secret manager or deployment environment; never commit `.env`.
- [ ] Keep `.env.example` placeholder-only; verify no secret appears in source, build output, logs, screenshots, or reports.
- [ ] Generate a unique JWT signing secret of at least 32 characters; rotate local development secrets as needed.
- [ ] Set `APP_ENV=production`; explicitly set HTTPS `CORS_ORIGINS` and TLS CA configuration.
- [ ] Do not use MySQL `root` for the application, migration, or Admin provisioning in production.

## Database and Migrations

- [ ] Provision separate least-privilege runtime, migration, and Admin-provisioning MySQL accounts.
- [ ] Restrict runtime privileges to required DML; do not grant schema ownership, DDL, or superuser access.
- [ ] Review Alembic upgrade SQL and operations against a staging backup before execution.
- [ ] Take a verified backup before each migration; apply migrations through the deployment pipeline.
- [ ] Confirm migration head, all expected tables/views, foreign keys, indexes, uniqueness and check constraints after migration.
- [ ] Resolve the PostgreSQL target stated in `SRS.md` and `docs/03-database-design.md` versus the MySQL implementation before design approval. Do not execute `database/schema.sql` against MySQL.

## Transport and Application Security

- [ ] Terminate HTTPS at a trusted endpoint; redirect or reject HTTP in production.
- [ ] Confirm protected API routes reject unauthenticated requests and no public registration exists.
- [ ] Review token storage, expiry, revocation, CSRF assumptions, trusted proxy handling, and login throttling.
- [ ] Run dependency vulnerability scans and remediate/accept findings with an owner and due date.
- [ ] Test SQL injection, XSS, CORS, authorization boundaries, and error handling using an approved security test plan.
- [ ] Verify logs exclude passwords, access tokens, database URLs, and unnecessary student/payment data.
- [ ] Review export scope and spreadsheet-formula injection protections before enabling exports.

## Personal Data and Operations

- [ ] Approve collected student fields, access policy, retention, correction/deletion process, and legal obligations.
- [ ] Encrypt database storage and backups; restrict operational access and record privileged access.
- [ ] Define backup schedule, retention, encryption, RPO/RTO, ownership, and alerting.
- [ ] Restore a backup to an isolated environment and verify linked student/enrollment/fee/payment/certificate records and balances.
- [ ] Document migration rollback/recovery, incident response, service monitoring, and support ownership.
- [ ] Run integration, browser, accessibility, performance, and recovery gates in staging; retain evidence.

## Admin Account Security

- [ ] Confirm an authorized operator-provided Admin identifier and perform secure bootstrap only when no Admin exists.
- [ ] Read the password interactively; use the application's Argon2 hashing path. Never place it in arguments, scripts, tickets, or logs.
- [ ] Confirm there is no public Admin registration and test password reset/token revocation.
- [ ] Do not reuse MySQL credentials as Admin login credentials.
- [ ] Current local database state is contaminated by test-generated rows; 42 Admin accounts were observed. Do not bootstrap, reset, or use its Admins until reviewed by the database owner and the intended identifier is confirmed.
