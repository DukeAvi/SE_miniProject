# Software Test Plan (STP)

## Document control

- **Project:** Blood Bank Management System (BBMS), Team 9
- **Version:** 1.1
- **Date:** 2026-11-14
- **Status:** Final classroom handoff plan; verification gaps and owner-approved waivers are explicit
- **Plan owner:** Avaneesh Ganesh Aroor, QA Lead
- **Frozen application snapshot:** `7b66a31c9550b4c7c2135aa6bc02b3c22290bab9`
- **Latest backend test baseline:** `fd0e96f81c49013c6a26fcfd7e6a811e4b97055b` (2026-11-09)
- **Change record:** Version 1.1 replaces the date, tool, schedule and structure assumptions from the submitted v1.0 draft; it aligns the test strategy with the implemented Django API and Next.js interface, moves Security Validation to §5.1, retains compatibility coverage as §5.4, and records current evidence and limitations.

This document describes the verification approach and the latest evidence available on 2026-11-14. It does not claim that the entire frozen application was re-tested on this document's date. The current RTM is [RTM-execution.md](reports/RTM-execution.md).

## 1. Introduction

### 1.1 Purpose

This plan defines how the BBMS requirements are tested, who owns each activity, which environments and tools were actually used, and what evidence is available for the classroom handoff. Test outcomes are recorded in the RTM and linked reports. A closed issue, a merged PR, or an owner waiver is not itself a passing test result.

### 1.2 Scope

The plan covers the Django REST Framework API, PostgreSQL persistence and scheduled services, the Next.js role dashboards, and security and operational controls. It traces all 34 functional, non-functional and security requirement IDs present in `backlog/issues.json` to their SAD design IDs and test IDs. It records automated, integration, browser, performance, security, reliability and recovery evidence, including explicit gaps.

The frozen classroom application snapshot is `7b66a31c9550b4c7c2135aa6bc02b3c22290bab9`. The final backend suite evidence was produced at `fd0e96f81c49013c6a26fcfd7e6a811e4b97055b`; UI evidence was produced against the dashboard candidate `8366159b92f89609fc2845f7864a67e02a639d53` and reviewed again before the freeze. Those revisions are identified separately in the RTM.

### 1.3 References and traceability sources

- Team 9 BBMS SRS v1.0, dated 2026-09-03; its PDF is not present in this repository checkout. The requirement keys and design/test mappings below are taken from the committed `backlog/issues.json` and the previous execution RTM. The source SRS must be supplied or published by its owner for final evaluator cross-check.
- Team 9 BBMS Software Architecture and Design Specification v1.0, dated 2026-10-04; design register and testability hooks are in §3.8.
- Submitted Team 9 Software Test Plan v1.0, dated 2026-09-17; superseded by this version.
- `backlog/issues.json`, the stable requirement/design/test manifest.
- [Authoritative RTM](reports/RTM-execution.md), [QA execution summary](reports/QA-002-execution-summary.md), [system validation report](reports/system-validation-report.md), [TC-UX-01](TC-UX-01.md), and [release-readiness record](release-readiness.md).

The SAD §3.8.2 still names the old STP mapping (5.1 compatibility and 5.4 security). This plan follows the evaluator decision recorded in issue #181: §5.1 is Security Validation and §5.4 is compatibility. The SAD/SRS source PDFs are not changed by this issue; DukeAvi should reconcile their cross-references in the owner-controlled document revision.

### 1.4 Definitions

- **BBMS:** Blood Bank Management System.
- **FR / NFR / SR:** functional / non-functional / security requirement.
- **SRS / SAD / STP / RTM:** Software Requirements Specification / Software Architecture and Design Specification / Software Test Plan / Requirements Traceability Matrix.
- **P, Partial, NR, F, Waived:** pass within stated scope / partial evidence / not run / observed failure / explicitly not executed with an owner-approved classroom limitation. Waived is never equivalent to Pass.
- **Tested revision:** the commit whose code is represented by the cited execution. A later documentation commit does not change that code revision.

## 2. Test items

1. Django API: authentication, profiles, donations, inventory, requests, notifications, reports, administration and audit.
2. Next.js web client: Donor, Recipient, Staff and Admin dashboards, session/CSRF integration, forms, responsive behavior and accessibility.
3. Background processing: inventory expiry, notification delivery, monitoring and backup/restore workflows.
4. Security and deployment configuration: role enforcement, input validation, sensitive-log filtering, TLS, headers, health checks and recovery.
5. Data and integrations: PostgreSQL as the deployment database; SQLite is used for the ordinary automated test suite; Redis/Celery are used for scheduled/background processing; notifications use the console/mock adapter in the classroom environment.

## 3. Features to be tested

The complete requirement-to-design-to-test mapping is in the RTM. Functional coverage includes registration/authentication/profile (`BBMS-F-001` to `F-004`), donor appointments and eligibility (`F-010` to `F-013`), verified inventory and expiry (`F-020` to `F-024`), request submission/review/fulfillment/history/compatibility (`F-030` to `F-034`), notification/reporting (`F-040` to `F-042`), and administration/audit (`F-050` to `F-051`).

Non-functional coverage includes performance (`BBMS-NF-001`), availability (`NF-002`), credential/log protection (`NF-003`), audit retention (`NF-004`), accessible responsive dashboards (`NF-005`), and backup/recovery (`NF-006`). Security coverage includes TLS (`BBMS-SR-001`), authorization (`SR-002`), input validation/injection defense (`SR-003`), security-event audit (`SR-004`), and session expiry (`SR-005`).

Representative test specifications with preconditions, steps, expected results, IDs and evidence are in §13. They are examples within the full manifest and do not replace the linked issue acceptance criteria.

## 4. Features not to be tested and execution limits

### 4.1 Out of scope

- Physical blood testing, laboratory equipment internals, and clinical diagnosis.
- External hospital systems beyond the documented BBMS interfaces.
- The internal delivery pipelines of third-party email/SMS providers; the classroom adapter is console/mock.
- Reliability of the database engine itself.
- Production data, production IAM, production alert routing, or production capacity; all committed test records are synthetic.

### 4.2 In-scope checks with incomplete or waived evidence

These remain in scope and are not reclassified as out of scope: four remaining PostgreSQL-only row-lock cases; actual screen-reader/manual accessibility verification; representative-user UAT; a measured monthly availability window; an external deployed-endpoint TLS inspection; and an operational restore with measured RPO/RTO. The 2026-11-09 release record says the owner accepted the classroom handoff with the stated human-check limitations. That disposition is a waiver for this handoff, not test execution or evaluator approval.

## 5. Test approach and strategy

### Test levels and entry/exit criteria

- **Unit:** pure eligibility and compatibility rules, validation, permission policy, and small service logic.
- **Integration/API:** Django services, database constraints, audit/ledger transactions, request ownership, notifications and scheduled jobs.
- **System/deployment:** API-backed role workflows, Docker Compose, TLS, health/readiness, process recovery and encrypted backup/restore.
- **Performance:** the approved 20-user synthetic normal-load profile for inventory search and dashboard donation reports.
- **Acceptance:** representative-user UAT and actual screen-reader review were planned but were not performed; the owner waived these for the classroom closure as recorded in the release record.

Entry criteria for a fresh run: identify the exact commit; use a clean isolated synthetic database; apply migrations; provision only synthetic role accounts and fixtures; confirm the test environment; record tool versions and timezone. Exit criteria for a claim of full requirement acceptance: every planned check has an observed result and evidence, critical defects are resolved or accepted with an explicit owner disposition, and every gap remains visible in the RTM. The classroom freeze does not satisfy the unperformed checks by implication.

### 5.1 Security Validation

Security testing covers the following controls, with positive and negative cases where applicable:

- HTTPS redirect, TLS 1.2/1.3 acceptance, TLS 1.0/1.1 rejection, HSTS/security headers, and encrypted PostgreSQL transport (`BBMS-SR-001`).
- Server-side role/ownership checks across Donor, Recipient, Staff and Admin, including denial behavior and sensitive-service enforcement (`BBMS-F-003`, `BBMS-SR-002`).
- Schema and boundary validation, injection-shaped input, ORM/query safety, response headers, and sanitized errors (`BBMS-SR-003`). A comprehensive independent fuzz campaign was not run.
- Password hashing, sensitive-field log filtering, security-event audit coverage, and idle/absolute session expiry (`BBMS-NF-003`, `BBMS-SR-004`, `BBMS-SR-005`).

Evidence is limited to the automated suite and the local/CI deployment checks listed in §13 and the RTM. No independent penetration test or external production TLS inspection is claimed.

### 5.2 Scheduled job testing

Expiry tests use the `as_of_date` hook and cover exact expiry boundaries, already-expired units, repeated runs, overlap protection, batching and a mid-run failure. Backup checks exercise encrypted dump/restore in CI and verify restored synthetic data. CI does not prove production object-store durability, external IAM, alert routing, or the 24-hour RPO/four-hour RTO in a deployed environment.

### 5.3 Role-based access and permission matrix

The test oracle is the SAD permission matrix. The automated policy suite checks 21 protected operations against Donor, Recipient, Staff and Admin (84 role-operation cells), including expected allow/deny behavior. UI visibility is convenience only; authorization remains enforced by Django. Browser review did not execute Admin or Staff mutations, so those UI mutation paths are not marked fully accepted solely from read-path evidence.

### 5.4 Blood type compatibility matrix

Compatibility remains safety-critical and retains the existing `TC-Req-05` identifier. Tests cover all 64 ABO/Rh donor-recipient pairs for each of four components (256 component/pair combinations), invalid values, incompatible fulfillment rejection, and the component-aware pure functions. The full automated matrix passed at the backend evidence revision.

## 6. Test environment, data and tools actually used

### 6.1 Backend

- Python 3.14.6, Django 5.2.18 and pytest 9.1.1 for the 2026-11-09 backend run.
- SQLite in-memory database (`bbms.settings_test`) for the 650-pass suite. Five PostgreSQL-specific tests are skipped under SQLite and are not counted as passes.
- PostgreSQL 16 CI service for deployment/TLS, encrypted backup/restore, process-recovery, performance and the dedicated low-stock concurrency workflow steps. The final CI run #42578040297 passed; only the low-stock concurrency check is among the five SQLite-skipped cases with a separate PostgreSQL result. Four other row-lock cases remain without PostgreSQL execution evidence.
- Django checks/migration validation, Ruff, GitHub Actions, Docker Compose, Coverage.py 7.17.2 and Apache JMeter 5.6.3 as listed in the execution records.

### 6.2 Web client

- Next.js 16.4.5, React 19.3.0, Node 22.23.2, Chromium and axe accessibility scans.
- Local synthetic accounts only; browser checks used the real Django API and same-origin proxy. Desktop/mobile screenshots are under `docs/qa/screenshots/`.
- Keyboard/mobile interactions and DOM announcements were checked in the browser. No NVDA/VoiceOver session or representative-user session was run.

### 6.3 Test data and tools not evidenced as run

Use synthetic `.example.test` identities and generated inventory/request records. Never use live donor, recipient, patient or clinical records. A Postman collection exists, but the final report set does not include a Postman execution log. Selenium and Jest from the original v1.0 draft are not the tools used by the current application. JMeter was run for the recorded 20-user profile; other production load profiles were not measured.

## 7. Test schedule and actual execution dates

The original September/October schedule is superseded by the implemented Sprint 1/Sprint 2 delivery dates. Actual evidence dates are:

- 2026-11-05: initial QA baseline on `f693371`; 639 passed, 1 failed, 5 SQLite skips. The report fixture failure was filed as #174.
- 2026-11-04: audit-retention checks (67 passed) and JMeter profile (20 synthetic users) produced separate evidence; dates reflect each run's recorded timestamp, not this plan's publication date.
- 2026-11-06: #178 fixed the date-dependent report fixture; #176 merged audit retention.
- 2026-11-09: backend rerun at `fd0e96f`; 650 passed, 0 failed, 5 skipped in 99.86 seconds. Dashboard review, CI deployment checks, release record and owner disposition were updated.
- 2026-11-14: this Test Plan/RTM/index revision prepared from the merged evidence. No application tests were rerun for this documentation change.

Actual UAT, screen-reader, four remaining PostgreSQL concurrency cases, monthly availability, and operational RPO/RTO dates are not available because those executions did not occur.

## 8. Test deliverables

- This versioned source and its matching PDF.
- [Authoritative RTM](reports/RTM-execution.md).
- QA execution, unit, system-validation, line-coverage and branch-coverage reports.
- [TC-UX-01](TC-UX-01.md) and committed desktop/mobile screenshots.
- [Release-readiness record](release-readiness.md), [Sprint 2 handoff](../demos/sprint-2-summary.md), and applicable operations evidence.
- Defect history #174 / fix PR #178, retained as historical evidence; the defect is resolved and is not a current failing test.

## 9. Roles and responsibilities

- **QA Lead - Avaneesh Ganesh Aroor:** maintain this plan and RTM, coordinate evidence, distinguish current results from history, and record gaps without converting them to passes.
- **Test Engineer - Ayush Kumar:** owns final test execution and the Unit, System Validation, Code Coverage and Branch Coverage reports; provides exact revision, commands, environment and explicit skips.
- **Development Lead / review owner - Avrit Sharma (@DukeAvi):** reviews requirement/design deviations, triages defects, owns SRS/SAD revisions and approves any waiver or release disposition.
- **Product Owner - Ayushman Dey:** defines product acceptance and UAT/waiver disposition.
- **Contributors:** execute only their assigned issue/branch and provide reproducible evidence through its PR.

## 10. Risks and mitigations

- **Concurrency masked by SQLite:** keep all five SQLite skips explicit; run PostgreSQL-specific cases. The dedicated low-stock case passed in CI; four other cases remain open as evidence gaps.
- **Compatibility error:** preserve full 256-cell component-aware coverage and recheck compatibility during fulfillment.
- **Time/date flakiness:** freeze dates and use explicit `as_of_date`; #174 is preserved as a historical failure and #178 as its fix.
- **Inaccurate security numbering:** align this plan with issue #181, retain compatibility, and flag the stale SAD §3.8.2 references for owner revision.
- **Overclaiming accessibility, availability, recovery or UAT:** report partial/waived states and keep the owner-approved classroom limits distinct from production readiness.
- **Sensitive data exposure:** use generated synthetic data and sanitize logs/reports; commit no secrets or live records.

## 11. Assumptions and dependencies

- The frozen classroom application revision is `7b66a31c9550b4c7c2135aa6bc02b3c22290bab9`; the latest backend automated evidence is `fd0e96f81c49013c6a26fcfd7e6a811e4b97055b`.
- PostgreSQL is the deployment database. SQLite is suitable for ordinary deterministic tests but cannot establish row-lock correctness.
- Test accounts and records are synthetic; the notification provider is console/mock.
- SRS v1.0 is referenced by the SAD but its file is not present in this repository. Until its owner supplies/publishes it, the RTM keys/design/test IDs are reconciled against the manifest and SAD, and the missing SRS is an explicit review input.
- The owner-directed classroom closure in `docs/qa/release-readiness.md` is not a production readiness or evaluator acceptance claim.

## 12. Suspension and resumption criteria

Suspend execution when the isolated environment is unavailable for more than four hours, test data is corrupted, a release candidate changes during the run, or a blocking defect prevents reliable interpretation of more than 30 percent of planned cases. Preserve logs and original failure evidence. Resume only after the environment/build is identified and stable, affected fixtures are reset, and the rerun revision is recorded. These operational criteria do not retrospectively change any result.

## 13. Test case specifications and traceability

The following representative cases include reproducible preconditions, steps, expected outcomes and evidence references. Result labels refer to the evidence listed, not to a new execution on 2026-11-14.

### TC-Auth-01 - Public registration

- **Traceability:** `BBMS-F-001` / `DS-001` / `TC-Auth-01`.
- **Preconditions:** isolated test database; no real identities; unique synthetic email/phone available.
- **Steps:** submit valid Donor and Recipient registrations; retry with duplicate email and phone; omit or malform required fields; attempt Staff/Admin role values; inspect persisted password hash and sanitized logs.
- **Expected:** one account per valid registration; duplicate/malformed/privileged-role attempts return field-level or generic documented errors; no partial records; password is one-way hashed and absent from logs/responses.
- **Evidence/result:** `tests/integration/accounts/test_registration.py`, `tests/integration/accounts/test_sensitive_logging.py`; **Pass** on backend baseline `fd0e96f`.

### TC-Auth-02 - Session login, logout and expiry

- **Traceability:** `BBMS-F-002` / `DS-002` / `TC-Auth-02`; `BBMS-SR-005` is additionally mapped to `DS-SR-005` / `TC-Sec-05` in the RTM.
- **Preconditions:** synthetic Donor/Recipient accounts and CSRF-enabled API client; short configured expiry for boundary tests.
- **Steps:** obtain CSRF token; log in with correct and incorrect credentials; compare failure responses; exceed throttle; log out; reuse the prior session; advance past idle and absolute limits.
- **Expected:** valid login creates an HttpOnly server-side session and correct role route; failures are generic and throttled; logout/expiry invalidates the session and returns the standard unauthenticated response.
- **Evidence/result:** `tests/integration/accounts/test_authentication.py`; **Pass** for automated cases at `fd0e96f`.

### TC-Auth-03 - Role and ownership matrix

- **Traceability:** `BBMS-F-003` / `DS-003` / `TC-Auth-03`; `BBMS-SR-002` / `DS-SR-002` / `TC-Sec-02`.
- **Preconditions:** one synthetic account for each role and representative owned/foreign records.
- **Steps:** exercise all 21 protected operation codes for Donor, Recipient, Staff and Admin; attempt foreign-object access; compare each response to the SAD role matrix.
- **Expected:** the 84 role-operation cells match the matrix, ownership is enforced, and protected denials do not reveal foreign records.
- **Evidence/result:** `tests/unit/core/test_permissions.py`; 84-cell matrix **Pass** on `fd0e96f`.

### TC-Don-01 - Appointment capacity and duplicate booking

- **Traceability:** `BBMS-F-010` / `DS-010` / `TC-Don-01`; duplicate control also maps `BBMS-F-012` / `DS-012` / `TC-Don-03`.
- **Preconditions:** synthetic eligible donor, slot with known capacity, and active appointment state reset.
- **Steps:** book an available slot; retry the same active donor/slot; submit competing bookings at the capacity boundary; run the PostgreSQL row-lock tests against an isolated PostgreSQL database.
- **Expected:** valid booking is recorded once; duplicate active booking is rejected; capacity is never exceeded under concurrency.
- **Evidence/result:** `tests/integration/donors/test_appointment_booking.py`; non-concurrent/constraint checks **Pass** at `fd0e96f`. Two PostgreSQL concurrency cases were skipped on SQLite and have no recorded PostgreSQL run: **Partial**.

### TC-Don-04 - Eligibility boundaries

- **Traceability:** `BBMS-F-013` / `DS-013` / `TC-Don-04`.
- **Preconditions:** frozen date and synthetic donor records immediately below, at and above age, weight and donation-interval limits.
- **Steps:** evaluate the pure eligibility function at each boundary; exercise booking/recording paths where the rule is integrated.
- **Expected:** eligibility follows the approved age, weight and interval boundaries consistently; rejected attempts do not create booking/donation records.
- **Evidence/result:** `tests/unit/donors/test_eligibility.py` and donor integration tests; **Pass** at `fd0e96f`.

### TC-Inv-03 - Transactional stock transition

- **Traceability:** `BBMS-F-022` / `DS-022` / `TC-Inv-03`.
- **Preconditions:** synthetic available unit, Staff actor, fixed as-of date and empty ledger/audit rows for the fixture.
- **Steps:** apply each valid transition; attempt invalid transitions; inject audit failure; attempt duplicate concurrent reservations on PostgreSQL.
- **Expected:** valid state, one append-only ledger row and audit event commit atomically; invalid/failing transitions leave unit, ledger and audit unchanged; concurrent reservation cannot change the same unit twice.
- **Evidence/result:** `tests/integration/inventory/test_stock_transitions.py`; transition/rollback/immutability checks **Pass** on `fd0e96f`; the PostgreSQL row-lock case was SQLite-skipped and remains unverified: **Partial**.

### TC-Inv-05 - Daily expiry job

- **Traceability:** `BBMS-F-024` / `DS-024` / `TC-Inv-05`.
- **Preconditions:** synthetic available units before, at and after the approved expiry boundary; fixed `as_of_date`.
- **Steps:** run the daily job; repeat for the same date; simulate a batch failure; inspect job run, ledger and audit rows.
- **Expected:** eligible units become EXPIRED once and are excluded from availability; reruns are idempotent; partial failure is reported and safely resumable.
- **Evidence/result:** `tests/integration/inventory/test_expiry_job.py`; **Pass** at `fd0e96f`.

### TC-Req-03 - Reserve and issue safely

- **Traceability:** `BBMS-F-032` / `DS-032` / `TC-Req-03`.
- **Preconditions:** approved synthetic request; compatible, available, unexpired units with known expiry/group order; Staff actor.
- **Steps:** reserve by FEFO with exact-group preference; issue with an idempotency key; repeat the same key; induce insufficient stock/invalid state; run concurrent reservation on PostgreSQL.
- **Expected:** compatible units are selected; repeat is idempotent; invalid/failed/concurrent operations do not issue one unit twice or leave partial allocation/ledger/audit/notification state.
- **Evidence/result:** `tests/integration/requests/test_fulfillment.py`; functional, rollback and idempotency cases **Pass** at `fd0e96f`; PostgreSQL concurrency case skipped on SQLite and not separately run: **Partial**.

### TC-Req-05 - Component-aware ABO/Rh compatibility

- **Traceability:** `BBMS-F-034` / `DS-034` / `TC-Req-05`.
- **Preconditions:** deterministic pure-function test inputs for eight ABO/Rh groups and four components.
- **Steps:** evaluate all 64 donor/recipient pairings for each component; check invalid inputs; attempt incompatible fulfillment.
- **Expected:** every compatible pair is accepted, every incompatible pair is rejected, and invalid values fail safely.
- **Evidence/result:** `tests/unit/requests/test_compatibility.py`; 256 component/pair cases **Pass** at `fd0e96f`.

### TC-Report-01 - Date-filtered operational reports

- **Traceability:** `BBMS-F-042` / `DS-042` / `TC-Report-01`.
- **Preconditions:** synthetic donations, transactions, requests and issues with fixed timestamps inside/outside the requested date range; authorized Staff/Admin.
- **Steps:** request each report and pagination/export path; compare aggregate/detail scope; run the grouped inventory summary regression test.
- **Expected:** date filters and role privacy are consistent; deterministic fixture falls within the queried day; grouped counts match the fixtures.
- **Evidence/result:** `tests/integration/adminops/test_operational_reports.py`; historical failure from #174 is retained, then #178 fixed the fixture; report suite 27 passed and #425780 CI passed. Current disposition: **Pass** at `fd0e96f`.

### TC-Sec-01 - Credential and transport protection

- **Traceability:** `BBMS-NF-003` / `DS-NF-003` / `TC-Sec-01`; `BBMS-SR-001` / `DS-SR-001` / `TC-Sec-01`.
- **Preconditions:** synthetic credentials; isolated Docker Compose TLS certificates; no production endpoint or secret.
- **Steps:** inspect stored password hashes and logs; exercise HTTPS, HTTP redirect, headers, TLS 1.2/1.3, rejection of TLS 1.0/1.1, and PostgreSQL TLS/hostname validation.
- **Expected:** password is Argon2 hashed; sensitive values are filtered; configured transport/security policies are enforced.
- **Evidence/result:** `tests/integration/accounts/test_sensitive_logging.py`, `tests/unit/core/test_tls_settings.py`, `scripts/test_tls_deployment.sh`, CI run #42578040297. `BBMS-NF-003`: **Pass**. `BBMS-SR-001`: **Partial** because no external deployed-endpoint inspection was performed.

### TC-Sec-03 - Input validation and injection defense

- **Traceability:** `BBMS-SR-003` / `DS-SR-003` / `TC-Sec-03`.
- **Preconditions:** synthetic API account and known valid payloads for login, donor, inventory and request flows.
- **Steps:** submit malformed, boundary and injection-shaped fields; inspect responses and persisted state; check required security headers.
- **Expected:** invalid input is rejected without partial writes or sensitive error detail; database access remains parameterized and browser output is escaped.
- **Evidence/result:** `tests/integration/inventory/test_input_security.py` and security validation tests at `fd0e96f`; automated validation **Pass**, full independent fuzz campaign not run, so overall requirement disposition **Partial**.

### TC-Audit-02 - One-year audit retention

- **Traceability:** `BBMS-NF-004` / `DS-NF-004` / `TC-Audit-02`.
- **Preconditions:** synthetic audit events immediately before, exactly at and after the UTC one-year cutoff.
- **Steps:** run dry-run; execute authorized purge; simulate delete failure; attempt ordinary model/queryset deletion; search retained records.
- **Expected:** only eligible old rows are removed after explicit execution; cutoff/newer rows remain; run events are recorded and failures roll back safely.
- **Evidence/result:** [audit retention report](audit-retention.md): 67 audit tests passed on `98fb14177b6acb94abd0ea70553f0d8893e9113f`; PR #176 merged and full suite rerun at `fd0e96f`. Automated retention checks: **Pass**; deployment database-role boundary is an operational limitation.

### TC-UX-01 - Role dashboards, keyboard and responsive behavior

- **Traceability:** `BBMS-NF-005` / `DS-NF-005` / `TC-UX-01`.
- **Preconditions:** synthetic Donor, Recipient, Staff and Admin accounts; Chromium; desktop 1440x1000 and mobile 390x844 viewports.
- **Steps:** sign in per role; inspect authorized views; run axe scans; navigate mobile controls by keyboard; submit a rejected form; inspect live announcements, focus, layout and screenshots.
- **Expected:** roles see permitted data; visible labels/focus and readable status/errors; layout fits viewport; failed forms retain user input.
- **Evidence/result:** [TC-UX-01](TC-UX-01.md), screenshots, PR #177. Browser/axe/mobile checks passed. Actual screen-reader session and representative-user UAT were not performed and were waived for the classroom handoff: **Partial (waived gap)**.

### TC-Perf-01 - Normal-load response time

- **Traceability:** `BBMS-NF-001` / `DS-NF-001` / `TC-Perf-01`.
- **Preconditions:** isolated PostgreSQL 16, 10,000 synthetic completed donations and 10,000 units, 100 synthetic donor profiles, two-worker Gunicorn, and 20 synthetic authenticated users.
- **Steps:** ramp users over 30 seconds; run 330 seconds with 250 ms think time; exclude the first 30 seconds; collect inventory search and 30-day donation report latencies and failure codes.
- **Expected:** p95 at or below 3,000 ms for both flows with zero failed/non-200 samples.
- **Evidence/result:** JMeter run #41807600683 and `docs/operations/performance.md`: 11,392 search samples, p95 18 ms; 11,390 report samples, p95 16 ms; zero failures/non-200. Benchmark profile **Pass** for the owner-approved 20-user classroom load. The overall workflow first failed later at a separate Prometheus-rule assertion; the corrected rule was subsequently validated by successful CI run #42578040297. No production-capacity claim is made.

### TC-Reli-01 - Readiness and process recovery

- **Traceability:** `BBMS-NF-002` / `DS-NF-002` / `TC-Reli-01`.
- **Preconditions:** isolated Compose deployment with database, web, worker and Beat services.
- **Steps:** query `/healthz`; stop/restart dependent database and application processes; verify sanitized unavailable response and recovery; inspect the external probe/alert configuration.
- **Expected:** readiness returns only non-sensitive state; supervised processes recover; monitoring distinguishes failed probes and maintenance.
- **Evidence/result:** CI run #42578040297 passed Docker restart, TLS and health checks; [availability guide](../operations/availability.md) documents the monthly calculation. No measured monthly uptime window exists: **Partial**.

### TC-DR-01 - Encrypted backup and restore

- **Traceability:** `BBMS-NF-006` / `DS-NF-006` / `TC-DR-01`.
- **Preconditions:** isolated PostgreSQL 16 source and spare target, synthetic data, temporary S3-compatible storage and CI-only encryption material.
- **Steps:** create encrypted archive and integrity marker; restore to an empty separate database; validate restored records; separately time an operational restore before claiming RPO/RTO.
- **Expected:** archive integrity/authentication is checked; restore does not overwrite a non-empty/source database; synthetic values are recovered; measured recovery stays within 24-hour RPO/four-hour RTO.
- **Evidence/result:** CI run #42578040297 passed the encrypted backup/restore drill; [backup/restore guide](../operations/database-backups.md) describes the checks. Production offsite durability, operator-witnessed elapsed time and measured RPO/RTO are absent: **Partial**.

### TC-Notif-01 - Request status notifications

- **Traceability:** `BBMS-F-040` / `DS-040` / `TC-Notif-01`.
- **Preconditions:** synthetic Recipient request, Staff decision, mock/console provider.
- **Steps:** exercise approved, rejected, held and fulfilled transitions; dispatch once and retry; inspect ownership and sanitized failure state.
- **Expected:** one transactional outbox row per configured transition; retries are bounded; users see only their notifications; provider failure does not roll back a clinical status change.
- **Evidence/result:** `tests/integration/notifications/test_notification_delivery.py`; **Pass** at `fd0e96f`.

## 14. Test metrics and reporting

- **Backend final rerun:** 655 collected; 650 passed, 0 failed, 5 skipped in 99.86 seconds at `fd0e96f`. The five skipped PostgreSQL row-lock tests are not passes. Four still lack PostgreSQL execution evidence; the low-stock concurrency path passed separately in CI run #42578040297.
- **Historical coverage only:** 90.32% line and 82.74% branch coverage were measured at `f693371ba0fce6d5d7d57e03ff2aa6dfff47d8f2` on 2026-11-05. No fresh coverage run is reported for the frozen application snapshot; do not present those percentages as fresh `7b66a31` coverage.
- **Performance:** approved 20-user synthetic profile p95 was 18 ms for inventory search and 16 ms for dashboard report; zero failed/non-200 samples. This is not a production-capacity measurement.
- **Availability:** no complete monthly observation window or 99.5% monthly result is attached.
- **Defects:** original date fixture failure #174 is historical; #178 corrected it. Current backend rerun has zero test failures.
- **Reporting:** preserve command, date/timezone, environment, tested revision, collected/pass/fail/skip counts, evidence links, defect/waiver disposition and owner. Do not calculate product defect density without a valid size denominator.

## 15. Approvals and disposition

The project owner directed final classroom closure on 2026-11-09 and accepted the limitations recorded in [release-readiness.md](release-readiness.md). That is a classroom waiver, not proof of UAT, external screen-reader acceptance, production uptime, external TLS inspection or measured production recovery. The original approval signature blocks in v1.0 were blank; no new evaluator or user signatures are invented here. Issue #181 PR review is the document review record for this revision.
