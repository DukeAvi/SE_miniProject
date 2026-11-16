# Final System Validation Report

## Purpose and evidence

This report consolidates system-level checks for the API-backed browser application, deployment configuration, background services, performance baseline, and four role workflows.

- **Final automated source:** `827819fa6b17d283c0886a5a71005935c3aaeddc`
- **Application source:** `daa75f5864ab9e56b53b8c3c735f14c53c349681` (merged PR #186)
- **Browser walkthrough source:** `aca01be032edce62cbe92524dea42c21857c760e`
- **Browser environment:** Chromium, Next.js production build, real local Django API, disposable synthetic accounts
- **Deployment evidence:** successful CI run [42578040297](https://github.com/DukeAvi/SE_miniProject/actions/runs/42578040297)

## Backend and contract validation

| Check | Procedure and observed result | Evidence |
| --- | --- | --- |
| Regression suite | 671 collected; 666 passed, zero failed, five SQLite row-lock skips. The five skipped cases separately passed on PostgreSQL. | [Unit report](unit-test-report.md) |
| Django and migration consistency | Django checks passed; no migration drift was reported; the audit onboarding migration was applied in the disposable browser database. | Final execution record |
| API contract and Postman parity | 36 documented operations and 37 Postman requests were checked; 35 operations resolve in Django. The legacy donor-detail route is superseded by the final Staff lookup/profile flow. | [API guide](../../api/README.md) |
| Authorization and ownership | The 21-operation × four-role policy matrix passed, and direct service authorization checks cover sensitive workflows. | [RTM](RTM-execution.md) |
| Compatibility | All 256 component-aware donor/recipient combinations passed, including invalid inputs and fulfillment rechecks. | [Unit report](unit-test-report.md) |

## Four-role workflow validation

| Role | Workflow actually exercised | Result |
| --- | --- | --- |
| Donor | Fresh public registration, incomplete-profile guidance, Staff verification, appointment booking and cancellation, own history access | Pass |
| Recipient | Aggregate availability, request submission, rejected-input preservation and accessible validation alert | Pass |
| Staff | Donor lookup/selection, donation recording, linked blood-unit creation, request approval, reservation and issue | Pass |
| Admin | Managed Staff-account creation and access to administrative workspace controls | Pass |

The walkthrough used the real session/CSRF API with Django role and ownership checks.

## Browser, responsive and accessibility validation

| Check | Observed result | Evidence |
| --- | --- | --- |
| axe scans | Zero WCAG A/AA and WCAG 2.1 A/AA violations for Donor, Recipient, Staff and Admin screens | [Browser result](../evidence/browser-2026-11-16.json) |
| Form behaviour | Invalid recipient input stayed populated and exposed an accessibility alert; donor profile guidance and Staff verification were exercised | [TC-UX-01](../TC-UX-01.md) |
| Keyboard/mobile | Keyboard-operated mobile navigation was exercised at 390 × 844 with no page-width overflow | [TC-UX-01](../TC-UX-01.md) |
| Desktop/mobile captures | Role-specific screenshots are committed for all four roles | [screenshots](../screenshots/) |


## Deployment, security and recovery validation

| Area | Recorded result | Evidence |
| --- | --- | --- |
| Secure transport | Isolated CI checks accepted TLS 1.2/1.3, rejected obsolete TLS versions, checked redirects, HSTS/security headers and database TLS. | [TLS script](../../../scripts/test_tls_deployment.sh) and CI run 42578040297 |
| Process recovery and health | Compose deployment, readiness/health behaviour, container restart and monitoring-rule checks passed in CI. | [Availability guide](../../operations/availability.md) |
| Backup and restore | CI completed encrypted PostgreSQL backup and restore with synthetic data. | [Backup guide](../../operations/database-backups.md) |
| Input and sensitive-data protection | Automated tests cover input validation, injection-shaped values, password hashing, log filtering, audit events and session expiry. | [RTM](RTM-execution.md) |
| Audit retention | Controlled one-year retention and purge checks passed with synthetic rows, including boundary, rollback and mutation-blocking cases. | [Retention evidence](../audit-retention.md) |

## Performance validation

The recorded TC-Perf-01 benchmark used PostgreSQL 16, 20 authenticated synthetic users, a 30-second ramp and a five-minute measured window. It produced 11,392 inventory-search samples at p95 **18 ms** and 11,390 dashboard-report samples at p95 **16 ms**, with zero failed or non-200 samples. The threshold was p95 at or below 3,000 ms for each flow.

Raw JMeter artifacts were attached to [run 41807600683](https://github.com/DukeAvi/SE_miniProject/actions/runs/41807600683); the procedure and query-plan context are retained in the [performance guide](../../operations/performance.md).

## Requirement coverage

The [RTM](RTM-execution.md) contains the result for all 34 planned functional, non-functional and security IDs.

## Evidence files

- [Final execution result](../evidence/final-execution.json)
- [Browser workflow evidence](../evidence/browser-2026-11-16.json)
- [Performance evidence](../../operations/performance.md)
- [Release readiness record](../release-readiness.md)
